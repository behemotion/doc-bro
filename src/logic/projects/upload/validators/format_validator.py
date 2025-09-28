"""
File format validation service

Handles validation of file formats and content including:
- MIME type detection and validation
- File size validation
- Content-based format verification
- Project-specific format restrictions
"""

import hashlib
import logging
import mimetypes
from pathlib import Path
from typing import Any

import magic

from src.logic.projects.models.project import ProjectType
from src.logic.projects.models.validation import FileValidationResult, ValidationResult

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


class FileValidator:
    """Service for validating file formats and content"""

    def __init__(self):
        # Initialize magic for MIME type detection
        try:
            self.magic_mime = magic.Magic(mime=True)
            self.magic_available = True
        except Exception as e:
            logger.warning(f"python-magic not available, falling back to mimetypes: {e}")
            self.magic_available = False

        # Default format restrictions by project type
        self.default_formats = {
            ProjectType.DATA: [
                # Documents
                "pdf", "txt", "md", "rst", "html", "htm", "xml", "json", "yaml", "yml",
                "docx", "doc", "odt", "rtf", "tex", "csv", "tsv",
                # Code files
                "py", "js", "ts", "java", "cpp", "c", "h", "hpp", "cs", "php", "rb", "go", "rs"
            ],
            ProjectType.STORAGE: [
                # All common file types
                "pdf", "txt", "md", "html", "json", "xml", "csv",
                "jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp", "svg",
                "mp3", "wav", "flac", "ogg", "m4a", "aac",
                "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm",
                "zip", "tar", "gz", "bz2", "7z", "rar", "xz",
                "exe", "msi", "deb", "rpm", "dmg", "pkg"
            ],
            ProjectType.CRAWLING: [
                # Web content
                "html", "htm", "xml", "css", "js", "json", "pdf", "txt", "md"
            ]
        }

        # MIME type mappings for validation
        self.mime_type_groups = {
            "text": ["text/plain", "text/html", "text/css", "text/javascript", "text/xml"],
            "document": [
                "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.oasis.opendocument.text", "application/rtf"
            ],
            "image": ["image/jpeg", "image/png", "image/gif", "image/bmp", "image/tiff", "image/webp", "image/svg+xml"],
            "audio": ["audio/mpeg", "audio/wav", "audio/flac", "audio/ogg", "audio/m4a", "audio/aac"],
            "video": ["video/mp4", "video/avi", "video/quicktime", "video/x-msvideo", "video/webm"],
            "archive": ["application/zip", "application/x-tar", "application/gzip", "application/x-7z-compressed"],
            "code": ["text/x-python", "application/javascript", "text/x-java-source", "text/x-c"]
        }

    async def validate_file_format(
        self,
        file_path: str,
        allowed_formats: list[str],
        project_type: ProjectType | None = None
    ) -> FileValidationResult:
        """Validate file format against allowed list"""
        try:
            path = Path(file_path)

            if not path.exists():
                return FileValidationResult(
                    valid=False,
                    errors=[f"File not found: {file_path}"],
                    warnings=[],
                    file_path=file_path
                )

            # Get file info
            file_info = await self.get_file_metadata(file_path)

            # Check file extension
            file_extension = path.suffix.lower().lstrip('.')

            # If no allowed formats specified, use defaults for project type
            if not allowed_formats and project_type:
                allowed_formats = self.default_formats.get(project_type, [])

            # Validate extension
            if allowed_formats and file_extension not in allowed_formats:
                return FileValidationResult(
                    valid=False,
                    errors=[f"File format '{file_extension}' not allowed. Allowed formats: {', '.join(allowed_formats)}"],
                    warnings=[],
                    file_path=file_path,
                    file_size=file_info.get("file_size"),
                    mime_type=file_info.get("mime_type")
                )

            # Validate MIME type consistency
            detected_mime = file_info.get("mime_type", "")
            expected_mime = mimetypes.guess_type(file_path)[0]

            warnings = []
            if expected_mime and detected_mime and detected_mime != expected_mime:
                warnings.append(f"MIME type mismatch: detected '{detected_mime}', expected '{expected_mime}'")

            # Additional validation for specific project types
            if project_type:
                type_validation = await self._validate_for_project_type(file_path, file_info, project_type)
                if not type_validation.valid:
                    return FileValidationResult(
                        valid=False,
                        errors=type_validation.errors,
                        warnings=warnings + type_validation.warnings,
                        file_path=file_path,
                        file_size=file_info.get("file_size"),
                        mime_type=file_info.get("mime_type")
                    )
                warnings.extend(type_validation.warnings)

            return FileValidationResult(
                valid=True,
                errors=[],
                warnings=warnings,
                file_path=file_path,
                file_size=file_info.get("file_size"),
                mime_type=file_info.get("mime_type")
            )

        except Exception as e:
            logger.error(f"Error validating file format for {file_path}: {e}")
            return FileValidationResult(
                valid=False,
                errors=[f"Format validation error: {str(e)}"],
                warnings=[],
                file_path=file_path
            )

    async def validate_file_size(
        self,
        file_path: str,
        max_size: int
    ) -> ValidationResult:
        """Validate file size against limit"""
        try:
            path = Path(file_path)

            if not path.exists():
                return ValidationResult(
                    valid=False,
                    errors=[f"File not found: {file_path}"],
                    warnings=[]
                )

            file_size = path.stat().st_size

            if file_size > max_size:
                size_mb = file_size / (1024 * 1024)
                limit_mb = max_size / (1024 * 1024)
                return ValidationResult(
                    valid=False,
                    errors=[f"File size {size_mb:.2f}MB exceeds limit of {limit_mb:.2f}MB"],
                    warnings=[]
                )

            # Warning for large files (>50% of limit)
            warnings = []
            if file_size > max_size * 0.5:
                size_mb = file_size / (1024 * 1024)
                warnings.append(f"Large file: {size_mb:.2f}MB")

            return ValidationResult(
                valid=True,
                errors=[],
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Error validating file size for {file_path}: {e}")
            return ValidationResult(
                valid=False,
                errors=[f"Size validation error: {str(e)}"],
                warnings=[]
            )

    async def validate_file_content(
        self,
        file_path: str,
        project_type: ProjectType
    ) -> ValidationResult:
        """Validate file content for project type"""
        try:
            path = Path(file_path)

            if not path.exists():
                return ValidationResult(
                    valid=False,
                    errors=[f"File not found: {file_path}"],
                    warnings=[]
                )

            # Get file metadata
            file_info = await self.get_file_metadata(file_path)
            mime_type = file_info.get("mime_type", "")

            # Content validation based on project type
            if project_type == ProjectType.DATA:
                return await self._validate_data_project_content(file_path, mime_type)
            elif project_type == ProjectType.STORAGE:
                return await self._validate_storage_project_content(file_path, mime_type)
            elif project_type == ProjectType.CRAWLING:
                return await self._validate_crawling_project_content(file_path, mime_type)

            return ValidationResult(valid=True, errors=[], warnings=[])

        except Exception as e:
            logger.error(f"Error validating file content for {file_path}: {e}")
            return ValidationResult(
                valid=False,
                errors=[f"Content validation error: {str(e)}"],
                warnings=[]
            )

    async def get_file_metadata(self, file_path: str) -> dict[str, Any]:
        """Extract comprehensive file metadata"""
        try:
            path = Path(file_path)
            stat = path.stat()

            # Basic file info
            metadata = {
                "filename": path.name,
                "file_size": stat.st_size,
                "file_extension": path.suffix.lower().lstrip('.'),
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "is_symlink": path.is_symlink(),
                "permissions": oct(stat.st_mode)[-3:]
            }

            # MIME type detection
            if self.magic_available:
                try:
                    metadata["mime_type"] = self.magic_mime.from_file(str(path))
                except Exception as e:
                    logger.debug(f"Magic MIME detection failed for {file_path}: {e}")
                    # Fallback to mimetypes
                    mime_type, _ = mimetypes.guess_type(str(path))
                    metadata["mime_type"] = mime_type or "application/octet-stream"
            else:
                mime_type, _ = mimetypes.guess_type(str(path))
                metadata["mime_type"] = mime_type or "application/octet-stream"

            # File hash for integrity
            metadata["sha256"] = await self._calculate_file_hash(file_path)

            # Additional metadata based on file type
            if metadata["mime_type"].startswith("text/"):
                metadata.update(await self._get_text_file_metadata(file_path))
            elif metadata["mime_type"].startswith("image/"):
                metadata.update(await self._get_image_metadata(file_path))

            return metadata

        except Exception as e:
            logger.error(f"Error getting file metadata for {file_path}: {e}")
            return {
                "filename": Path(file_path).name,
                "file_size": 0,
                "mime_type": "application/octet-stream"
            }

    async def _validate_for_project_type(
        self,
        file_path: str,
        file_info: dict[str, Any],
        project_type: ProjectType
    ) -> ValidationResult:
        """Validate file for specific project type requirements"""
        mime_type = file_info.get("mime_type", "")
        file_size = file_info.get("file_size", 0)

        warnings = []
        errors = []

        if project_type == ProjectType.DATA:
            # Data projects prefer text-based formats for processing
            if not any(mime_type.startswith(prefix) for prefix in ["text/", "application/pdf", "application/json"]):
                warnings.append("Non-text format may not be processed for vector storage")

            # Large files may cause processing issues
            if file_size > 50 * 1024 * 1024:  # 50MB
                warnings.append("Large file may cause processing delays")

        elif project_type == ProjectType.STORAGE:
            # Storage projects have fewer restrictions but warn about very large files
            if file_size > 1024 * 1024 * 1024:  # 1GB
                warnings.append("Very large file - ensure sufficient storage space")

        elif project_type == ProjectType.CRAWLING:
            # Crawling projects should only have web content
            if not any(mime_type.startswith(prefix) for prefix in ["text/html", "text/", "application/pdf"]):
                errors.append("Only web content formats are supported for crawling projects")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def _validate_data_project_content(self, file_path: str, mime_type: str) -> ValidationResult:
        """Validate content for data projects"""
        warnings = []

        # Check if file is readable as text
        if mime_type.startswith("text/"):
            try:
                # Try to read file and check encoding
                with open(file_path, encoding='utf-8') as f:
                    content = f.read(1024)  # Read first 1KB
                    if not content.strip():
                        warnings.append("File appears to be empty")
            except UnicodeDecodeError:
                warnings.append("File contains non-UTF-8 characters")
            except Exception as e:
                warnings.append(f"Could not read file content: {str(e)}")

        return ValidationResult(valid=True, errors=[], warnings=warnings)

    async def _validate_storage_project_content(self, file_path: str, mime_type: str) -> ValidationResult:
        """Validate content for storage projects"""
        warnings = []

        # Basic integrity check
        try:
            with open(file_path, 'rb') as f:
                # Try to read first few bytes
                first_bytes = f.read(512)
                if not first_bytes:
                    warnings.append("File appears to be empty")
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Cannot read file: {str(e)}"],
                warnings=[]
            )

        return ValidationResult(valid=True, errors=[], warnings=warnings)

    async def _validate_crawling_project_content(self, file_path: str, mime_type: str) -> ValidationResult:
        """Validate content for crawling projects"""
        errors = []
        warnings = []

        # Crawling projects should only have web-related content
        if mime_type.startswith("text/html"):
            # Validate HTML content
            try:
                with open(file_path, encoding='utf-8') as f:
                    content = f.read(1024)
                    if not content.strip().startswith(('<!DOCTYPE', '<html', '<HTML')):
                        warnings.append("File does not appear to be valid HTML")
            except Exception as e:
                warnings.append(f"Could not validate HTML content: {str(e)}")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.debug(f"Could not calculate hash for {file_path}: {e}")
            return ""

    async def _get_text_file_metadata(self, file_path: str) -> dict[str, Any]:
        """Get metadata specific to text files"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()
                return {
                    "line_count": content.count('\n') + 1,
                    "char_count": len(content),
                    "word_count": len(content.split()),
                    "encoding": "utf-8"
                }
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, encoding='latin-1') as f:
                    content = f.read()
                    return {
                        "line_count": content.count('\n') + 1,
                        "char_count": len(content),
                        "word_count": len(content.split()),
                        "encoding": "latin-1"
                    }
            except Exception:
                return {"encoding": "binary"}
        except Exception as e:
            logger.debug(f"Could not get text metadata for {file_path}: {e}")
            return {}

    async def _get_image_metadata(self, file_path: str) -> dict[str, Any]:
        """Get metadata specific to image files"""
        try:
            # Try to get image dimensions using PIL if available
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    return {
                        "image_width": img.width,
                        "image_height": img.height,
                        "image_mode": img.mode,
                        "image_format": img.format
                    }
            except ImportError:
                # PIL not available
                return {}
        except Exception as e:
            logger.debug(f"Could not get image metadata for {file_path}: {e}")
            return {}

    def get_supported_formats(self, project_type: ProjectType) -> list[str]:
        """Get list of supported formats for project type"""
        return self.default_formats.get(project_type, [])

    def is_format_supported(self, file_extension: str, project_type: ProjectType) -> bool:
        """Check if file format is supported for project type"""
        supported_formats = self.get_supported_formats(project_type)
        return file_extension.lower().lstrip('.') in supported_formats

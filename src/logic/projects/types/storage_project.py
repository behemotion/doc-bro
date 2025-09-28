"""StorageProject handler for file storage and inventory management projects."""

import logging
from pathlib import Path
from typing import Any

from ...contracts.service_interfaces import StorageProjectContract
from ..models.config import ProjectConfig
from ..models.files import StorageFile, ValidationResult
from ..models.project import Project

logger = logging.getLogger(__name__)


class StorageProject(StorageProjectContract):
    """
    Handler for storage projects that specialize in file storage and inventory management.

    Provides file storage, organization, tagging, and search capabilities
    with comprehensive metadata tracking.
    """

    def __init__(self):
        """Initialize StorageProject handler."""
        pass

    async def initialize_project(self, project: Project) -> bool:
        """
        Initialize storage project with file storage and inventory systems.

        Args:
            project: Project instance to initialize

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing storage project: {project.name}")

            project_dir = Path(project.get_project_directory())

            # Create project-specific directories
            directories = [
                project_dir / "files",
                project_dir / "archive",
                project_dir / "thumbnails",
                project_dir / "temp",
                project_dir / "exports",
                project_dir / "logs"
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

            # Create storage configuration
            storage_config = {
                'project_name': project.name,
                'project_type': 'storage',
                'enable_compression': project.settings.get('enable_compression', True),
                'auto_tagging': project.settings.get('auto_tagging', True),
                'full_text_indexing': project.settings.get('full_text_indexing', True),
                'storage_encryption': project.settings.get('storage_encryption', False),
                'created_at': project.created_at.isoformat(),
                'status': 'initialized'
            }

            config_file = project_dir / "storage_config.json"
            import json
            with open(config_file, 'w') as f:
                json.dump(storage_config, f, indent=2)

            # Initialize file inventory database
            await self._initialize_inventory_database(project)

            # Initialize search index
            await self._initialize_search_index(project)

            logger.info(f"Successfully initialized storage project: {project.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize storage project {project.name}: {e}")
            return False

    async def cleanup_project(self, project: Project) -> bool:
        """
        Clean up storage project resources.

        Args:
            project: Project instance to clean up

        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            logger.info(f"Cleaning up storage project: {project.name}")

            # Archive all files if requested
            backup_enabled = project.settings.get('backup_on_cleanup', True)
            if backup_enabled:
                await self._archive_all_files(project)

            # Export file inventory
            await self._export_file_inventory(project)

            # Clean up temporary files
            project_dir = Path(project.get_project_directory())
            temp_dir = project_dir / "temp"
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)

            # Clear search indexes
            await self._cleanup_search_index(project)

            logger.info(f"Successfully cleaned up storage project: {project.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup storage project {project.name}: {e}")
            return False

    async def validate_settings(self, settings: ProjectConfig) -> ValidationResult:
        """
        Validate settings for storage projects.

        Args:
            settings: ProjectConfig to validate

        Returns:
            ValidationResult indicating validation status
        """
        errors = []
        warnings = []

        # Storage projects are flexible with formats
        if settings.allowed_formats == []:
            errors.append("At least one file format must be allowed")

        # Validate compression settings
        if settings.enable_compression is not None and not isinstance(settings.enable_compression, bool):
            errors.append("enable_compression must be a boolean value")

        if settings.auto_tagging is not None and not isinstance(settings.auto_tagging, bool):
            errors.append("auto_tagging must be a boolean value")

        if settings.full_text_indexing is not None and not isinstance(settings.full_text_indexing, bool):
            errors.append("full_text_indexing must be a boolean value")

        if settings.storage_encryption is not None and not isinstance(settings.storage_encryption, bool):
            errors.append("storage_encryption must be a boolean value")

        # Check for incompatible settings
        incompatible_settings = [
            'crawl_depth', 'rate_limit', 'user_agent', 'chunk_size', 'embedding_model'
        ]
        for setting in incompatible_settings:
            if hasattr(settings, setting) and getattr(settings, setting) is not None:
                warnings.append(f"Setting '{setting}' is not used by storage projects")

        # Validate file size limits
        if settings.max_file_size and settings.max_file_size > 1073741824:  # 1GB
            warnings.append("Large file size limit may impact performance")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def get_default_settings(self) -> ProjectConfig:
        """
        Get default settings for storage projects.

        Returns:
            ProjectConfig with storage-specific defaults
        """
        return ProjectConfig(
            max_file_size=104857600,  # 100MB
            allowed_formats=['*'],  # All formats allowed
            enable_compression=True,
            auto_tagging=True,
            full_text_indexing=True,
            storage_encryption=False,
            concurrent_uploads=5,
            retry_attempts=3,
            timeout_seconds=120
        )

    async def store_file(
        self,
        project: Project,
        file_path: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Store file and return file ID.

        Args:
            project: Project instance
            file_path: Path to file to store
            metadata: Optional file metadata

        Returns:
            File ID of stored file

        Raises:
            ValueError: If file doesn't exist or validation fails
            RuntimeError: If storage operation fails
        """
        logger.info(f"Storing file in project {project.name}: {file_path}")

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ValueError(f"File does not exist: {file_path}")

        try:
            # Validate file size
            file_size = file_path_obj.stat().st_size
            max_size = project.settings.get('max_file_size', 104857600)
            if file_size > max_size:
                raise ValueError(f"File size {file_size} exceeds limit {max_size}")

            # Validate file format
            allowed_formats = project.settings.get('allowed_formats', ['*'])
            if '*' not in allowed_formats:
                file_ext = file_path_obj.suffix.lower().lstrip('.')
                if file_ext not in allowed_formats:
                    raise ValueError(f"File format '{file_ext}' not allowed")

            # Generate file ID and storage path
            file_id = await self._generate_file_id()
            storage_dir = Path(project.get_project_directory()) / "files"
            storage_path = storage_dir / f"{file_id}{file_path_obj.suffix}"

            # Copy file to storage
            import shutil
            shutil.copy2(str(file_path_obj), str(storage_path))

            # Calculate checksum
            checksum = StorageFile.calculate_file_checksum(str(storage_path))

            # Detect MIME type
            mime_type = await self._detect_mime_type(storage_path)

            # Create upload source for local file
            from ..models.upload import UploadSource, UploadSourceType
            local_source = UploadSource(
                type=UploadSourceType.LOCAL,
                location=str(file_path_obj.parent)
            )

            # Create StorageFile record
            storage_file = StorageFile(
                id=file_id,
                project_id=project.id,
                filename=file_path_obj.name,
                file_path=str(storage_path),
                file_size=file_size,
                mime_type=mime_type,
                upload_source=local_source,
                checksum=checksum,
                metadata=metadata or {}
            )

            # Auto-tag if enabled
            if project.settings.get('auto_tagging', True):
                auto_tags = await self._generate_auto_tags(storage_file)
                storage_file.add_tags(auto_tags)

            # Save file record
            await self._save_file_record(project, storage_file)

            # Update search index if enabled
            if project.settings.get('full_text_indexing', True):
                await self._index_file_for_search(project, storage_file)

            # Compress file if enabled
            if project.settings.get('enable_compression', True):
                await self._compress_file_if_beneficial(storage_file)

            logger.info(f"Successfully stored file {file_path_obj.name} with ID: {file_id}")
            return file_id

        except Exception as e:
            logger.error(f"Failed to store file {file_path}: {e}")
            raise RuntimeError(f"File storage failed: {e}")

    async def retrieve_file(self, project: Project, file_id: str, output_path: str) -> bool:
        """
        Retrieve stored file.

        Args:
            project: Project instance
            file_id: ID of file to retrieve
            output_path: Path where to copy the file

        Returns:
            True if retrieval successful, False otherwise

        Raises:
            ValueError: If file not found
            RuntimeError: If retrieval fails
        """
        logger.info(f"Retrieving file from project {project.name}: {file_id}")

        try:
            # Load file record
            storage_file = await self._load_file_record(project, file_id)
            if not storage_file:
                raise ValueError(f"File not found: {file_id}")

            # Check if file exists on disk
            if not Path(storage_file.file_path).exists():
                raise ValueError(f"File data missing for ID: {file_id}")

            # Verify file integrity
            if not storage_file.verify_integrity():
                raise RuntimeError(f"File integrity check failed for ID: {file_id}")

            # Copy file to output location
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

            import shutil
            shutil.copy2(storage_file.file_path, str(output_path_obj))

            # Record access
            storage_file.record_access()
            await self._save_file_record(project, storage_file)

            logger.info(f"Successfully retrieved file {file_id} to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to retrieve file {file_id}: {e}")
            raise RuntimeError(f"File retrieval failed: {e}")

    async def search_files(
        self,
        project: Project,
        query: str,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Search files in storage project.

        Args:
            project: Project instance
            query: Search query
            filters: Optional search filters

        Returns:
            List of matching files with metadata
        """
        try:
            logger.info(f"Searching files in project {project.name}: '{query}'")

            # Load all file records
            all_files = await self._load_all_file_records(project)

            # Apply text-based search
            matching_files = []
            query_lower = query.lower()

            for storage_file in all_files:
                # Search in filename, tags, and metadata
                searchable_text = (
                    storage_file.filename.lower() + " " +
                    " ".join(storage_file.tags) + " " +
                    " ".join(str(v) for v in storage_file.metadata.values())
                )

                if query_lower in searchable_text:
                    matching_files.append(storage_file)

            # Apply filters if provided
            if filters:
                matching_files = await self._apply_search_filters(matching_files, filters)

            # Convert to search result format
            results = []
            for storage_file in matching_files:
                result = {
                    'file_id': storage_file.id,
                    'filename': storage_file.filename,
                    'file_size': storage_file.file_size,
                    'mime_type': storage_file.mime_type,
                    'upload_date': storage_file.upload_date.isoformat(),
                    'tags': storage_file.tags,
                    'metadata': storage_file.metadata,
                    'checksum': storage_file.checksum,
                    'access_count': storage_file.access_count,
                    'last_accessed': storage_file.last_accessed.isoformat() if storage_file.last_accessed else None
                }
                results.append(result)

            # Sort by relevance (simple filename match preference)
            results.sort(key=lambda x: 0 if query_lower in x['filename'].lower() else 1)

            logger.info(f"Found {len(results)} files matching query: '{query}'")
            return results

        except Exception as e:
            logger.error(f"Search failed for project {project.name}: {e}")
            return []

    async def tag_file(self, project: Project, file_id: str, tags: list[str]) -> bool:
        """
        Add tags to stored file.

        Args:
            project: Project instance
            file_id: ID of file to tag
            tags: List of tags to add

        Returns:
            True if tagging successful, False otherwise

        Raises:
            ValueError: If file not found
        """
        try:
            logger.info(f"Adding tags to file {file_id} in project {project.name}: {tags}")

            # Load file record
            storage_file = await self._load_file_record(project, file_id)
            if not storage_file:
                raise ValueError(f"File not found: {file_id}")

            # Add tags
            storage_file.add_tags(tags)

            # Save updated record
            await self._save_file_record(project, storage_file)

            # Update search index
            if project.settings.get('full_text_indexing', True):
                await self._update_file_search_index(project, storage_file)

            logger.info(f"Successfully added {len(tags)} tags to file {file_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to tag file {file_id}: {e}")
            return False

    async def get_file_inventory(self, project: Project) -> list[dict[str, Any]]:
        """
        Get complete file inventory.

        Args:
            project: Project instance

        Returns:
            List of all files with metadata
        """
        try:
            all_files = await self._load_all_file_records(project)

            inventory = []
            for storage_file in all_files:
                file_info = {
                    'file_id': storage_file.id,
                    'filename': storage_file.filename,
                    'file_size': storage_file.file_size,
                    'file_size_display': storage_file.get_display_size(),
                    'mime_type': storage_file.mime_type,
                    'file_extension': storage_file.file_extension,
                    'upload_date': storage_file.upload_date.isoformat(),
                    'tags': storage_file.tags,
                    'metadata': storage_file.metadata,
                    'checksum': storage_file.checksum,
                    'access_count': storage_file.access_count,
                    'last_accessed': storage_file.last_accessed.isoformat() if storage_file.last_accessed else None,
                    'is_compressed': storage_file.is_compressed,
                    'compression_ratio': storage_file.compression_ratio,
                    'upload_source': {
                        'type': storage_file.upload_source.type.value,
                        'location': storage_file.upload_source.get_display_location()
                    }
                }
                inventory.append(file_info)

            # Sort by upload date (newest first)
            inventory.sort(key=lambda x: x['upload_date'], reverse=True)

            return inventory

        except Exception as e:
            logger.error(f"Failed to get file inventory for project {project.name}: {e}")
            return []

    async def get_project_stats(self, project: Project) -> dict[str, Any]:
        """
        Get project-specific statistics for storage projects.

        Args:
            project: Project instance

        Returns:
            Dictionary containing project statistics
        """
        try:
            all_files = await self._load_all_file_records(project)

            stats = {
                'type_specific_stats': {
                    'total_files': len(all_files),
                    'total_size': sum(f.file_size for f in all_files),
                    'total_size_display': self._format_bytes(sum(f.file_size for f in all_files)),
                    'file_types': {},
                    'tag_usage': {},
                    'compression_stats': {
                        'compressed_files': 0,
                        'compression_savings': 0
                    },
                    'access_stats': {
                        'total_accesses': sum(f.access_count for f in all_files),
                        'most_accessed': None,
                        'least_accessed': None
                    },
                    'upload_sources': {},
                    'largest_file': None,
                    'oldest_file': None,
                    'newest_file': None
                }
            }

            if all_files:
                # File type statistics
                for storage_file in all_files:
                    file_type = storage_file.file_extension or 'unknown'
                    stats['type_specific_stats']['file_types'][file_type] = \
                        stats['type_specific_stats']['file_types'].get(file_type, 0) + 1

                # Tag usage statistics
                for storage_file in all_files:
                    for tag in storage_file.tags:
                        stats['type_specific_stats']['tag_usage'][tag] = \
                            stats['type_specific_stats']['tag_usage'].get(tag, 0) + 1

                # Compression statistics
                compressed_files = [f for f in all_files if f.is_compressed]
                stats['type_specific_stats']['compression_stats']['compressed_files'] = len(compressed_files)

                # Access statistics
                most_accessed = max(all_files, key=lambda f: f.access_count)
                stats['type_specific_stats']['access_stats']['most_accessed'] = {
                    'filename': most_accessed.filename,
                    'access_count': most_accessed.access_count
                }

                # Upload source statistics
                for storage_file in all_files:
                    source_type = storage_file.upload_source.type.value
                    stats['type_specific_stats']['upload_sources'][source_type] = \
                        stats['type_specific_stats']['upload_sources'].get(source_type, 0) + 1

                # File extremes
                largest_file = max(all_files, key=lambda f: f.file_size)
                stats['type_specific_stats']['largest_file'] = {
                    'filename': largest_file.filename,
                    'size': largest_file.get_display_size()
                }

                oldest_file = min(all_files, key=lambda f: f.upload_date)
                stats['type_specific_stats']['oldest_file'] = {
                    'filename': oldest_file.filename,
                    'upload_date': oldest_file.upload_date.isoformat()
                }

                newest_file = max(all_files, key=lambda f: f.upload_date)
                stats['type_specific_stats']['newest_file'] = {
                    'filename': newest_file.filename,
                    'upload_date': newest_file.upload_date.isoformat()
                }

            return stats

        except Exception as e:
            logger.error(f"Failed to get project stats for {project.name}: {e}")
            return {'type_specific_stats': {}}

    # Private helper methods

    async def _generate_file_id(self) -> str:
        """Generate unique file ID."""
        import uuid
        return str(uuid.uuid4())

    async def _detect_mime_type(self, file_path: Path) -> str:
        """Detect MIME type of file."""
        # Simple MIME type detection based on extension
        mime_types = {
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.zip': 'application/zip',
            '.json': 'application/json',
            '.xml': 'application/xml'
        }

        file_ext = file_path.suffix.lower()
        return mime_types.get(file_ext, 'application/octet-stream')

    async def _generate_auto_tags(self, storage_file: StorageFile) -> list[str]:
        """Generate automatic tags for file."""
        tags = []

        # Add tag based on file extension
        if storage_file.file_extension:
            tags.append(f"type:{storage_file.file_extension}")

        # Add tag based on MIME type category
        if storage_file.mime_type.startswith('image/'):
            tags.append('image')
        elif storage_file.mime_type.startswith('video/'):
            tags.append('video')
        elif storage_file.mime_type.startswith('audio/'):
            tags.append('audio')
        elif storage_file.mime_type.startswith('text/'):
            tags.append('text')

        # Add size category tag
        if storage_file.file_size < 1024:  # < 1KB
            tags.append('size:tiny')
        elif storage_file.file_size < 1024 * 1024:  # < 1MB
            tags.append('size:small')
        elif storage_file.file_size < 10 * 1024 * 1024:  # < 10MB
            tags.append('size:medium')
        else:
            tags.append('size:large')

        return tags

    async def _initialize_inventory_database(self, project: Project) -> None:
        """Initialize file inventory database."""
        # Create file inventory database
        db_path = Path(project.get_project_directory()) / "inventory.db"

        # In a real implementation, this would create database tables
        # For now, create a simple JSON file for file storage
        inventory_file = Path(project.get_project_directory()) / "file_inventory.json"
        if not inventory_file.exists():
            import json
            with open(inventory_file, 'w') as f:
                json.dump([], f)

    async def _initialize_search_index(self, project: Project) -> None:
        """Initialize search index for files."""
        # Create search index configuration
        search_config = {
            'index_type': 'full_text',
            'fields': ['filename', 'tags', 'metadata'],
            'created_at': project.created_at.isoformat()
        }

        config_file = Path(project.get_project_directory()) / "search_config.json"
        import json
        with open(config_file, 'w') as f:
            json.dump(search_config, f, indent=2)

    async def _cleanup_search_index(self, project: Project) -> None:
        """Clean up search index."""
        search_config_file = Path(project.get_project_directory()) / "search_config.json"
        if search_config_file.exists():
            search_config_file.unlink()

    async def _archive_all_files(self, project: Project) -> None:
        """Archive all project files."""
        try:
            import shutil
            from datetime import datetime

            project_dir = Path(project.get_project_directory())
            files_dir = project_dir / "files"

            if files_dir.exists() and any(files_dir.iterdir()):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archive_name = f"{project.name}_files_{timestamp}"
                archive_path = project_dir / f"{archive_name}.tar.gz"

                shutil.make_archive(
                    str(project_dir / archive_name),
                    'gztar',
                    str(files_dir)
                )

                logger.info(f"Archived files for project {project.name} to: {archive_path}")

        except Exception as e:
            logger.warning(f"Failed to archive files for project {project.name}: {e}")

    async def _export_file_inventory(self, project: Project) -> None:
        """Export file inventory to JSON."""
        try:
            inventory = await self.get_file_inventory(project)

            export_file = Path(project.get_project_directory()) / "exports" / "file_inventory_export.json"
            export_file.parent.mkdir(exist_ok=True)

            import json
            with open(export_file, 'w') as f:
                json.dump(inventory, f, indent=2)

            logger.info(f"Exported file inventory for project {project.name}")

        except Exception as e:
            logger.warning(f"Failed to export inventory for project {project.name}: {e}")

    async def _save_file_record(self, project: Project, storage_file: StorageFile) -> None:
        """Save file record to project database."""
        try:
            inventory_file = Path(project.get_project_directory()) / "file_inventory.json"

            # Load existing inventory
            inventory_data = []
            if inventory_file.exists():
                import json
                with open(inventory_file) as f:
                    inventory_data = json.load(f)

            # Remove existing record if updating
            inventory_data = [item for item in inventory_data if item.get('id') != storage_file.id]

            # Add new/updated record
            file_dict = storage_file.dict()
            # Convert datetime objects to strings for JSON serialization
            for key, value in file_dict.items():
                if hasattr(value, 'isoformat'):
                    file_dict[key] = value.isoformat()

            inventory_data.append(file_dict)

            # Save updated inventory
            import json
            with open(inventory_file, 'w') as f:
                json.dump(inventory_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save file record for {storage_file.filename}: {e}")

    async def _load_file_record(self, project: Project, file_id: str) -> StorageFile | None:
        """Load file record by ID."""
        try:
            all_files = await self._load_all_file_records(project)
            for storage_file in all_files:
                if storage_file.id == file_id:
                    return storage_file
            return None

        except Exception as e:
            logger.error(f"Failed to load file record {file_id}: {e}")
            return None

    async def _load_all_file_records(self, project: Project) -> list[StorageFile]:
        """Load all file records for the project."""
        try:
            inventory_file = Path(project.get_project_directory()) / "file_inventory.json"

            if not inventory_file.exists():
                return []

            import json
            with open(inventory_file) as f:
                inventory_data = json.load(f)

            files = []
            for file_data in inventory_data:
                # Convert string dates back to datetime
                for date_field in ['upload_date', 'last_accessed']:
                    if date_field in file_data and isinstance(file_data[date_field], str):
                        from datetime import datetime
                        if file_data[date_field]:  # Handle None values
                            file_data[date_field] = datetime.fromisoformat(file_data[date_field])

                storage_file = StorageFile(**file_data)
                files.append(storage_file)

            return files

        except Exception as e:
            logger.error(f"Failed to load file records for project {project.name}: {e}")
            return []

    async def _index_file_for_search(self, project: Project, storage_file: StorageFile) -> None:
        """Index file for full-text search."""
        # In a real implementation, this would:
        # 1. Extract text content if possible
        # 2. Create search index entries
        # 3. Update search database
        logger.debug(f"Indexing file for search: {storage_file.filename}")

    async def _update_file_search_index(self, project: Project, storage_file: StorageFile) -> None:
        """Update file search index after changes."""
        await self._index_file_for_search(project, storage_file)

    async def _compress_file_if_beneficial(self, storage_file: StorageFile) -> None:
        """Compress file if it would be beneficial."""
        # Simple compression logic - only for text files > 1KB
        if (storage_file.mime_type.startswith('text/') and
            storage_file.file_size > 1024 and
            not storage_file.is_compressed):

            # In a real implementation, this would actually compress the file
            # For now, just mark as compressed with estimated ratio
            storage_file.is_compressed = True
            storage_file.compression_ratio = 0.7  # Estimated 30% reduction

    async def _apply_search_filters(
        self,
        files: list[StorageFile],
        filters: dict[str, Any]
    ) -> list[StorageFile]:
        """Apply search filters to file list."""
        filtered_files = files

        # Filter by file type
        if 'file_type' in filters:
            file_type = filters['file_type'].lower()
            filtered_files = [f for f in filtered_files if f.file_extension == file_type]

        # Filter by size range
        if 'min_size' in filters:
            min_size = int(filters['min_size'])
            filtered_files = [f for f in filtered_files if f.file_size >= min_size]

        if 'max_size' in filters:
            max_size = int(filters['max_size'])
            filtered_files = [f for f in filtered_files if f.file_size <= max_size]

        # Filter by date range
        if 'date_from' in filters:
            from datetime import datetime
            date_from = datetime.fromisoformat(filters['date_from'])
            filtered_files = [f for f in filtered_files if f.upload_date >= date_from]

        if 'date_to' in filters:
            from datetime import datetime
            date_to = datetime.fromisoformat(filters['date_to'])
            filtered_files = [f for f in filtered_files if f.upload_date <= date_to]

        # Filter by tags
        if 'tags' in filters:
            required_tags = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
            filtered_files = [f for f in filtered_files
                            if any(tag in f.tags for tag in required_tags)]

        return filtered_files

    def _format_bytes(self, bytes_count: int) -> str:
        """Format byte count as human-readable string."""
        if bytes_count < 1024:
            return f"{bytes_count} B"
        elif bytes_count < 1024 * 1024:
            return f"{bytes_count / 1024:.1f} KB"
        elif bytes_count < 1024 * 1024 * 1024:
            return f"{bytes_count / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_count / (1024 * 1024 * 1024):.1f} GB"

    def __str__(self) -> str:
        """String representation of StorageProject handler."""
        return "StorageProject(file storage and inventory management)"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return "StorageProject(type=storage, capabilities=[file_storage, inventory_management, search, tagging])"

"""
Validation models for projects logic

Contains validation result structures and error handling models.
"""

from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation operation"""
    valid: bool
    errors: list[str]
    warnings: list[str]

    def add_error(self, error: str) -> None:
        """Add an error to the validation result"""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result"""
        self.warnings.append(warning)

    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """Merge another validation result into this one"""
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings
        )

    @classmethod
    def success(cls, warnings: list[str] | None = None) -> 'ValidationResult':
        """Create a successful validation result"""
        return cls(valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(cls, errors: list[str], warnings: list[str] | None = None) -> 'ValidationResult':
        """Create a failed validation result"""
        return cls(valid=False, errors=errors, warnings=warnings or [])


@dataclass
class FileValidationResult(ValidationResult):
    """Extended validation result for file operations"""
    file_path: str | None = None
    file_size: int | None = None
    mime_type: str | None = None

    def add_file_error(self, error: str, file_path: str) -> None:
        """Add a file-specific error"""
        self.add_error(f"{file_path}: {error}")
        self.file_path = file_path


@dataclass
class UploadValidationResult(ValidationResult):
    """Validation result for upload operations"""
    source_accessible: bool = False
    credentials_valid: bool = False
    files_found: int = 0
    total_size: int = 0

    @classmethod
    def from_validation_result(
        cls,
        result: ValidationResult,
        source_accessible: bool = False,
        credentials_valid: bool = False,
        files_found: int = 0,
        total_size: int = 0
    ) -> 'UploadValidationResult':
        """Create upload validation result from base result"""
        return cls(
            valid=result.valid,
            errors=result.errors,
            warnings=result.warnings,
            source_accessible=source_accessible,
            credentials_valid=credentials_valid,
            files_found=files_found,
            total_size=total_size
        )

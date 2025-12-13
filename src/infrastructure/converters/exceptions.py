"""
Custom exceptions for document conversion.

These exceptions provide clear, actionable error messages for different
failure scenarios during document conversion.
"""


class ConverterError(Exception):
    """Base exception for all converter errors."""

    def __init__(self, message: str, details: dict[str, any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def get_user_message(self) -> str:
        """Get user-friendly error message with suggested actions."""
        return self.message


class FileNotReadableError(ConverterError):
    """File exists but cannot be read (permissions, corruption, etc.)."""

    def get_user_message(self) -> str:
        return (
            f"{self.message}\n\n"
            "Possible solutions:\n"
            "- Check file permissions\n"
            "- Verify the file is not open in another program\n"
            "- Ensure the file is not corrupted"
        )


class InvalidFileFormatError(ConverterError):
    """File format is invalid or corrupted."""

    def get_user_message(self) -> str:
        format_type = self.details.get('format', 'document')
        return (
            f"{self.message}\n\n"
            f"The file does not appear to be a valid {format_type}.\n"
            "Possible solutions:\n"
            f"- Verify the file is actually a {format_type}\n"
            "- Check if the file is corrupted\n"
            "- Try re-saving the file from the original application"
        )


class UnsupportedFileFormatError(ConverterError):
    """File format is not supported by the converter."""

    def get_user_message(self) -> str:
        supported = self.details.get('supported_formats', [])
        return (
            f"{self.message}\n\n"
            f"Supported formats: {', '.join(supported)}\n"
            "Possible solutions:\n"
            "- Convert the file to a supported format\n"
            "- Use a different conversion tool"
        )


class EncodingError(ConverterError):
    """Text encoding issues (not UTF-8, invalid characters, etc.)."""

    def get_user_message(self) -> str:
        encoding = self.details.get('encoding', 'UTF-8')
        return (
            f"{self.message}\n\n"
            f"Expected encoding: {encoding}\n"
            "Possible solutions:\n"
            "- Save the file with UTF-8 encoding\n"
            "- Convert the file encoding using a text editor\n"
            "- Remove any invalid characters"
        )


class FileTooLargeError(ConverterError):
    """File exceeds size limits for processing."""

    def get_user_message(self) -> str:
        size = self.details.get('size_mb', 0)
        limit = self.details.get('limit_mb', 0)
        return (
            f"{self.message}\n\n"
            f"File size: {size:.1f} MB\n"
            f"Maximum size: {limit:.1f} MB\n"
            "Possible solutions:\n"
            "- Split the document into smaller files\n"
            "- Compress images in the document\n"
            "- Remove unnecessary content"
        )


class ContentExtractionError(ConverterError):
    """Error extracting specific content (tables, formulas, etc.)."""

    def get_user_message(self) -> str:
        content_type = self.details.get('content_type', 'content')
        return (
            f"{self.message}\n\n"
            f"Failed to extract {content_type}.\n"
            "Note: This may result in incomplete conversion,\n"
            "but the rest of the document should be available."
        )


class DependencyError(ConverterError):
    """Required external dependency missing or failed."""

    def get_user_message(self) -> str:
        library = self.details.get('library', 'library')
        return (
            f"{self.message}\n\n"
            f"Missing or incompatible dependency: {library}\n"
            "Possible solutions:\n"
            f"- Install {library}: pip install {library}\n"
            "- Upgrade the library to the latest version\n"
            "- Check system requirements"
        )


class PasswordProtectedError(ConverterError):
    """Document is password protected."""

    def get_user_message(self) -> str:
        return (
            f"{self.message}\n\n"
            "The document is password protected.\n"
            "Possible solutions:\n"
            "- Remove password protection from the document\n"
            "- Provide the password (not currently supported)\n"
            "- Export an unprotected copy from the original application"
        )

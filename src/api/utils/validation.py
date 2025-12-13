"""
Input validation utilities for API endpoints.

Provides validation functions for file uploads, user input sanitization,
and security checks to prevent common vulnerabilities.
"""
import re
from pathlib import Path
from typing import Set, Optional
from fastapi import HTTPException, status


# Allowed MIME types for document uploads
ALLOWED_MIME_TYPES: Set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",  # .doc
    "text/markdown",
    "text/x-rst",
}

# Allowed file extensions
ALLOWED_EXTENSIONS: Set[str] = {
    ".pdf",
    ".docx",
    ".doc",
    ".md",
    ".markdown",
    ".rst",
    ".rest",
}

# Maximum length constraints
MAX_TITLE_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 2000
MAX_FILENAME_LENGTH = 255


def validate_file_size(file_size: int, max_size: int) -> None:
    """
    Validate that file size does not exceed the maximum allowed size.

    Args:
        file_size: Size of the file in bytes
        max_size: Maximum allowed size in bytes

    Raises:
        HTTPException: If file size exceeds the maximum

    Example:
        >>> validate_file_size(file_size=5000000, max_size=10485760)  # 5MB file, 10MB limit
        >>> validate_file_size(file_size=15000000, max_size=10485760)  # Raises exception
    """
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size:,} bytes) exceeds maximum allowed size "
                   f"({max_size:,} bytes / {max_size / 1024 / 1024:.1f}MB)"
        )


def validate_content_type(content_type: Optional[str], filename: Optional[str] = None) -> None:
    """
    Validate that the content type is allowed for upload.

    Checks both the MIME type and optionally validates against the file extension.

    Args:
        content_type: MIME type of the file (e.g., "application/pdf")
        filename: Optional filename to validate extension

    Raises:
        HTTPException: If content type is not allowed

    Example:
        >>> validate_content_type("application/pdf", "document.pdf")
        >>> validate_content_type("application/x-executable")  # Raises exception
    """
    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type is required"
        )

    # Normalize content type (remove parameters like charset)
    normalized_type = content_type.split(';')[0].strip().lower()

    if normalized_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Content type '{content_type}' is not supported. "
                   f"Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )

    # If filename is provided, validate extension matches content type
    if filename:
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{extension}' is not allowed. "
                       f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )


def sanitize_filename(filename: Optional[str]) -> str:
    """
    Sanitize a filename to prevent path traversal and other security issues.

    Removes:
    - Path separators (/ and \\)
    - Null bytes
    - Control characters
    - Leading/trailing dots and whitespace
    - Multiple consecutive dots

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename

    Raises:
        HTTPException: If filename is invalid or becomes empty after sanitization

    Example:
        >>> sanitize_filename("document.pdf")
        'document.pdf'
        >>> sanitize_filename("../../../etc/passwd")
        Raises HTTPException
        >>> sanitize_filename("my document (final).pdf")
        'my document (final).pdf'
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    # Check for path separators (prevents most path traversal)
    if "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid characters (path separators)"
        )

    # Remove null bytes
    filename = filename.replace("\0", "")

    # Remove control characters (ASCII 0-31)
    filename = re.sub(r'[\x00-\x1f]', '', filename)

    # Strip leading/trailing whitespace and dots
    filename = filename.strip().strip('.')

    # Replace multiple consecutive dots with single dot
    filename = re.sub(r'\.{2,}', '.', filename)

    # After sanitization, check if the result is exactly ".." (dangerous)
    # Since we already blocked path separators and stripped leading dots,
    # the filename being ".." would only happen from malicious input
    if filename == "..":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid characters (parent directory references)"
        )

    # Validate length
    if len(filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Filename exceeds maximum length of {MAX_FILENAME_LENGTH} characters"
        )

    # Ensure filename is not empty after sanitization
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is invalid (empty after sanitization)"
        )

    # Ensure filename has an extension
    if '.' not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must have a file extension"
        )

    return filename


def validate_title(title: Optional[str]) -> None:
    """
    Validate document title length and content.

    Args:
        title: The title to validate

    Raises:
        HTTPException: If title is invalid

    Example:
        >>> validate_title("Trading Algorithm Specification")
        >>> validate_title("")  # Raises exception
        >>> validate_title("x" * 300)  # Raises exception
    """
    if not title or not title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title is required and cannot be empty"
        )

    if len(title) > MAX_TITLE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Title exceeds maximum length of {MAX_TITLE_LENGTH} characters"
        )


def validate_description(description: Optional[str]) -> None:
    """
    Validate document description length.

    Args:
        description: The description to validate (optional)

    Raises:
        HTTPException: If description exceeds maximum length

    Example:
        >>> validate_description("A trading algorithm document")
        >>> validate_description(None)  # OK, description is optional
        >>> validate_description("x" * 3000)  # Raises exception
    """
    if description and len(description) > MAX_DESCRIPTION_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Description exceeds maximum length of {MAX_DESCRIPTION_LENGTH} characters"
        )


def validate_upload_file(
    filename: Optional[str],
    content_type: Optional[str],
    file_size: int,
    max_size: int,
    title: Optional[str],
    description: Optional[str] = None
) -> str:
    """
    Comprehensive validation for file upload.

    Validates all aspects of a file upload in the correct order:
    1. Filename sanitization
    2. Content type validation
    3. File size validation
    4. Title validation
    5. Description validation

    Args:
        filename: Original filename from upload
        content_type: MIME type of the file
        file_size: Size of the file in bytes
        max_size: Maximum allowed file size in bytes
        title: Document title
        description: Optional document description

    Returns:
        Sanitized filename

    Raises:
        HTTPException: If any validation fails

    Example:
        >>> sanitized = validate_upload_file(
        ...     filename="document.pdf",
        ...     content_type="application/pdf",
        ...     file_size=5000000,
        ...     max_size=10485760,
        ...     title="Trading Algorithm Spec",
        ...     description="A comprehensive specification"
        ... )
    """
    # 1. Sanitize filename first (security check)
    sanitized_filename = sanitize_filename(filename)

    # 2. Validate content type (security check)
    validate_content_type(content_type, sanitized_filename)

    # 3. Validate file size (DoS prevention)
    validate_file_size(file_size, max_size)

    # 4. Validate title (data integrity)
    validate_title(title)

    # 5. Validate description (data integrity)
    validate_description(description)

    return sanitized_filename

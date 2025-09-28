"""
TextTruncator service for text length management
"""

from typing import Optional
from ..models.enums import TruncationStrategy


class TextTruncator:
    """Service for intelligent text truncation handling"""

    def __init__(self):
        """Initialize text truncator"""
        pass

    def truncate_middle(self, text: str, max_length: int, ellipsis: str = "...") -> str:
        """
        Truncate text in the middle preserving start and end

        Args:
            text: Input text to truncate
            max_length: Maximum allowed length
            ellipsis: Characters to indicate truncation

        Returns:
            Truncated text with ellipsis in middle
        """
        if len(text) <= max_length:
            return text

        if max_length <= len(ellipsis):
            return ellipsis[:max_length]

        # Calculate how much text we can keep on each side
        available_length = max_length - len(ellipsis)
        start_length = (available_length + 1) // 2  # Favor the start slightly
        end_length = available_length - start_length

        return f"{text[:start_length]}{ellipsis}{text[-end_length:]}"

    def truncate_end(self, text: str, max_length: int, ellipsis: str = "...") -> str:
        """
        Truncate text at the end

        Args:
            text: Input text to truncate
            max_length: Maximum allowed length
            ellipsis: Characters to indicate truncation

        Returns:
            Truncated text with ellipsis at end
        """
        if len(text) <= max_length:
            return text

        if max_length <= len(ellipsis):
            return ellipsis[:max_length]

        return f"{text[:max_length - len(ellipsis)]}{ellipsis}"

    def truncate_with_strategy(self, text: str, max_length: int,
                             strategy: TruncationStrategy = TruncationStrategy.MIDDLE,
                             ellipsis: str = "...") -> str:
        """
        Truncate text using specified strategy

        Args:
            text: Input text to truncate
            max_length: Maximum allowed length
            strategy: Truncation strategy to use
            ellipsis: Characters to indicate truncation

        Returns:
            Truncated text according to strategy
        """
        if strategy == TruncationStrategy.MIDDLE:
            return self.truncate_middle(text, max_length, ellipsis)
        elif strategy == TruncationStrategy.END:
            return self.truncate_end(text, max_length, ellipsis)
        elif strategy == TruncationStrategy.NONE:
            return text
        else:
            raise ValueError(f"Unknown truncation strategy: {strategy}")

    def truncate_file_path(self, path: str, max_length: int, ellipsis: str = "...") -> str:
        """
        Truncate file path preserving filename and extension

        Args:
            path: File path to truncate
            max_length: Maximum allowed length
            ellipsis: Characters to indicate truncation

        Returns:
            Truncated path preserving important parts
        """
        if len(path) <= max_length:
            return path

        # Try to preserve the filename (last component)
        path_parts = path.split('/')
        if len(path_parts) > 1:
            filename = path_parts[-1]
            directory = '/'.join(path_parts[:-1])

            # If filename alone is too long, truncate it
            if len(filename) >= max_length - 3:  # Account for ellipsis and separator
                return self.truncate_middle(filename, max_length, ellipsis)

            # Calculate available space for directory
            available_for_dir = max_length - len(filename) - 1 - len(ellipsis)
            if available_for_dir > 0:
                truncated_dir = self.truncate_end(directory, available_for_dir, ellipsis)
                return f"{truncated_dir}/{filename}"

        # Fallback to middle truncation
        return self.truncate_middle(path, max_length, ellipsis)

    def truncate_url(self, url: str, max_length: int, ellipsis: str = "...") -> str:
        """
        Truncate URL preserving scheme and domain

        Args:
            url: URL to truncate
            max_length: Maximum allowed length
            ellipsis: Characters to indicate truncation

        Returns:
            Truncated URL preserving important parts
        """
        if len(url) <= max_length:
            return url

        # Try to preserve scheme and domain
        if "://" in url:
            scheme_domain, path = url.split("://", 1)
            if "/" in path:
                domain, path_part = path.split("/", 1)
                base = f"{scheme_domain}://{domain}"

                # If base alone is too long, truncate it
                if len(base) >= max_length - 3:
                    return self.truncate_middle(base, max_length, ellipsis)

                # Calculate available space for path
                available_for_path = max_length - len(base) - 1 - len(ellipsis)
                if available_for_path > 0:
                    truncated_path = self.truncate_end(path_part, available_for_path, ellipsis)
                    return f"{base}/{truncated_path}"

        # Fallback to middle truncation
        return self.truncate_middle(url, max_length, ellipsis)
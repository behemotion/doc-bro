"""Project type handlers."""

from .crawling_project import CrawlingProject
from .data_project import DataProject
from .storage_project import StorageProject

__all__ = [
    "CrawlingProject",
    "DataProject",
    "StorageProject"
]

"""Service for unified fill command with type-based routing."""

import logging
from typing import Optional, Dict, Any

from src.models.box_type import BoxType
from src.services.box_service import BoxService
from src.services.database import DatabaseError
from src.core.lib_logger import get_component_logger

logger = get_component_logger("fill_service")


class FillService:
    """
    Service for filling boxes with content using type-based routing.

    Routes fill operations to appropriate underlying services:
    - DRAG boxes -> Crawler service
    - RAG boxes -> Upload service
    - BAG boxes -> Storage service
    """

    def __init__(self, box_service: Optional[BoxService] = None):
        """Initialize fill service."""
        self.box_service = box_service or BoxService()

    async def initialize(self) -> None:
        """Initialize the fill service."""
        await self.box_service.initialize()

    async def fill(
        self,
        box_name: str,
        source: str,
        shelf_name: Optional[str] = None,
        **options
    ) -> Dict[str, Any]:
        """
        Fill a box with content based on its type.

        Args:
            box_name: Name of the box to fill
            source: Source URL or path
            shelf_name: Optional shelf context
            **options: Type-specific options

        Returns:
            Dictionary with operation result

        Raises:
            BoxNotFoundError: If box not found
            DatabaseError: If operation fails
        """
        await self.initialize()

        # Get the box to determine type
        box = await self.box_service.get_box_by_name(box_name)
        if not box:
            from src.models.box import BoxNotFoundError
            raise BoxNotFoundError(f"Box '{box_name}' not found")

        logger.info(f"Filling {box.type.value} box '{box_name}' from source: {source}")

        # Route based on box type
        try:
            if box.type == BoxType.DRAG:
                return await self._fill_drag(box, source, **options)
            elif box.type == BoxType.RAG:
                return await self._fill_rag(box, source, **options)
            elif box.type == BoxType.BAG:
                return await self._fill_bag(box, source, **options)
            else:
                raise DatabaseError(f"Unknown box type: {box.type}")

        except Exception as e:
            logger.error(f"Failed to fill box '{box_name}': {e}")
            return {
                'success': False,
                'box_name': box_name,
                'box_type': box.type.value,
                'source': source,
                'error': str(e)
            }

    async def _fill_drag(self, box, source: str, **options) -> Dict[str, Any]:
        """
        Fill a drag box using crawler service.

        Args:
            box: Box model
            source: Source URL
            **options: Crawler-specific options (max_pages, rate_limit, depth)

        Returns:
            Operation result
        """
        logger.info(f"Starting crawl operation for drag box '{box.name}'")

        # Extract drag-specific options
        max_pages = options.get('max_pages', box.max_pages or 100)
        rate_limit = options.get('rate_limit', box.rate_limit or 1.0)
        depth = options.get('depth', box.crawl_depth or 3)

        try:
            # TODO: Import and use actual crawler service
            # from src.logic.crawler.core.crawler import DocumentationCrawler
            # crawler = DocumentationCrawler()
            # result = await crawler.crawl_documentation(
            #     project_name=box.name,
            #     base_url=source,
            #     max_pages=max_pages,
            #     rate_limit=rate_limit,
            #     depth=depth
            # )

            # For now, simulate the operation
            logger.info(f"Crawling {source} into drag box '{box.name}' (max_pages={max_pages}, rate_limit={rate_limit}, depth={depth})")

            # Update box URL if different
            if box.url != source:
                await self._update_box_url(box, source)

            return {
                'success': True,
                'box_name': box.name,
                'box_type': 'drag',
                'source': source,
                'operation': 'crawl',
                'max_pages': max_pages,
                'rate_limit': rate_limit,
                'depth': depth,
                'message': f"Crawling {source} into drag box '{box.name}'..."
            }

        except Exception as e:
            raise DatabaseError(f"Failed to crawl {source}: {e}")

    async def _fill_rag(self, box, source: str, **options) -> Dict[str, Any]:
        """
        Fill a rag box using uploader service.

        Args:
            box: Box model
            source: Source path or URL
            **options: RAG-specific options (chunk_size, overlap)

        Returns:
            Operation result
        """
        logger.info(f"Starting document import for rag box '{box.name}'")

        # Extract rag-specific options
        chunk_size = options.get('chunk_size', 500)
        overlap = options.get('overlap', 50)

        try:
            # TODO: Import and use actual uploader service
            # from src.services.upload_service import UploadService
            # uploader = UploadService()
            # result = await uploader.upload_documents(
            #     project_name=box.name,
            #     source_path=source,
            #     chunk_size=chunk_size,
            #     overlap=overlap
            # )

            # For now, simulate the operation
            logger.info(f"Importing {source} into rag box '{box.name}' (chunk_size={chunk_size}, overlap={overlap})")

            return {
                'success': True,
                'box_name': box.name,
                'box_type': 'rag',
                'source': source,
                'operation': 'import',
                'chunk_size': chunk_size,
                'overlap': overlap,
                'message': f"Importing {source} into rag box '{box.name}'..."
            }

        except Exception as e:
            raise DatabaseError(f"Failed to import {source}: {e}")

    async def _fill_bag(self, box, source: str, **options) -> Dict[str, Any]:
        """
        Fill a bag box using storage service.

        Args:
            box: Box model
            source: Source path
            **options: Storage-specific options (recursive, pattern)

        Returns:
            Operation result
        """
        logger.info(f"Starting file storage for bag box '{box.name}'")

        # Extract bag-specific options
        recursive = options.get('recursive', False)
        pattern = options.get('pattern', '*')

        try:
            # TODO: Import and use actual storage service
            # from src.services.storage_service import StorageService
            # storage = StorageService()
            # result = await storage.store_files(
            #     project_name=box.name,
            #     source_path=source,
            #     recursive=recursive,
            #     pattern=pattern
            # )

            # For now, simulate the operation
            logger.info(f"Storing {source} into bag box '{box.name}' (recursive={recursive}, pattern={pattern})")

            return {
                'success': True,
                'box_name': box.name,
                'box_type': 'bag',
                'source': source,
                'operation': 'store',
                'recursive': recursive,
                'pattern': pattern,
                'message': f"Storing {source} into bag box '{box.name}'..."
            }

        except Exception as e:
            raise DatabaseError(f"Failed to store {source}: {e}")

    async def _update_box_url(self, box, new_url: str) -> None:
        """Update box URL if it has changed."""
        try:
            conn = self.box_service.db._connection
            await conn.execute(
                "UPDATE boxes SET url = ?, updated_at = ? WHERE id = ?",
                (new_url, __import__('datetime').datetime.now(timezone.utc).isoformat(), box.id)
            )
            await conn.commit()
            logger.info(f"Updated box '{box.name}' URL to: {new_url}")

        except Exception as e:
            logger.warning(f"Failed to update box URL: {e}")

    async def get_fill_options(self, box_name: str) -> Dict[str, Any]:
        """
        Get available fill options for a box based on its type.

        Args:
            box_name: Name of the box

        Returns:
            Dictionary of available options

        Raises:
            BoxNotFoundError: If box not found
        """
        await self.initialize()

        box = await self.box_service.get_box_by_name(box_name)
        if not box:
            from src.models.box import BoxNotFoundError
            raise BoxNotFoundError(f"Box '{box_name}' not found")

        if box.type == BoxType.DRAG:
            return {
                'type': 'drag',
                'description': 'Website crawling options',
                'options': {
                    'max_pages': {
                        'type': 'int',
                        'default': box.max_pages or 100,
                        'description': 'Maximum pages to crawl'
                    },
                    'rate_limit': {
                        'type': 'float',
                        'default': box.rate_limit or 1.0,
                        'description': 'Requests per second'
                    },
                    'depth': {
                        'type': 'int',
                        'default': box.crawl_depth or 3,
                        'description': 'Maximum crawl depth'
                    }
                }
            }

        elif box.type == BoxType.RAG:
            return {
                'type': 'rag',
                'description': 'Document import options',
                'options': {
                    'chunk_size': {
                        'type': 'int',
                        'default': 500,
                        'description': 'Text chunk size for processing'
                    },
                    'overlap': {
                        'type': 'int',
                        'default': 50,
                        'description': 'Chunk overlap in characters'
                    }
                }
            }

        elif box.type == BoxType.BAG:
            return {
                'type': 'bag',
                'description': 'File storage options',
                'options': {
                    'recursive': {
                        'type': 'bool',
                        'default': False,
                        'description': 'Include subdirectories'
                    },
                    'pattern': {
                        'type': 'str',
                        'default': '*',
                        'description': 'File pattern filter'
                    }
                }
            }

        else:
            return {
                'type': 'unknown',
                'description': 'Unknown box type',
                'options': {}
            }
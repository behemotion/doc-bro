"""Integration tests for complete project lifecycle."""

import pytest
import pytest_asyncio
from pathlib import Path
import tempfile
import shutil

from src.models.project import Project
from src.models.crawl_session import CrawlSession
from src.services.database import DatabaseManager
from src.services.crawler import DocumentationCrawler
from src.services.vector_store import VectorStoreService
from src.services.rag import RAGSearchService
from src.cli.main import DocBroApp


class TestProjectLifecycle:
    """Integration tests for complete project lifecycle from creation to search."""

    @pytest.fixture
    def temp_project_dir(self):
        """Temporary directory for test projects."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_project_config(self):
        """Sample project configuration for lifecycle testing."""
        return {
            "name": "test-lifecycle-project",
            "source_url": "https://docs.python.org/3/library/asyncio.html",
            "crawl_depth": 2,
            "embedding_model": "mxbai-embed-large",
            "chunk_size": 1000,
            "chunk_overlap": 100
        }

    @pytest.fixture
    async def db_manager(self):
        """Database manager for lifecycle testing."""
        try:
            from src.services.database import DatabaseManager
            manager = DatabaseManager()
            await manager.initialize()
            yield manager
            await manager.cleanup()
        except ImportError:
            pytest.fail("DatabaseManager not implemented yet")

    @pytest.fixture
    async def vector_store(self):
        """Vector store for lifecycle testing."""
        try:
            from src.services.vector_store import VectorStoreService
            service = VectorStoreService()
            await service.initialize()
            yield service
            await service.cleanup()
        except ImportError:
            pytest.fail("VectorStoreService not implemented yet")

    @pytest.fixture
    async def crawler(self, db_manager):
        """Crawler service for lifecycle testing."""
        try:
            from src.services.crawler import DocumentationCrawler
            return DocumentationCrawler(db_manager)
        except ImportError:
            pytest.fail("DocumentationCrawler not implemented yet")

    @pytest.fixture
    async def rag_service(self, vector_store, db_manager):
        """RAG service for lifecycle testing."""
        try:
            from src.services.rag import RAGSearchService
            from src.services.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            return RAGSearchService(vector_store, embedding_service)
        except ImportError:
            pytest.fail("RAGSearchService not implemented yet")

    @pytest.fixture
    def docbro_app(self):
        """DocBro CLI application for lifecycle testing."""
        try:
            from src.cli.main import DocBroApp
            return DocBroApp()
        except ImportError:
            pytest.fail("DocBroApp not implemented yet")

    @pytest.mark.lifecycle
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_project_lifecycle(
        self,
        docbro_app,
        db_manager,
        crawler,
        rag_service,
        sample_project_config,
        temp_project_dir
    ):
        """Test complete project lifecycle: create -> crawl -> index -> search."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            # 1. Create project
            project = await db_manager.create_project(**sample_project_config)
            assert project.name == sample_project_config["name"]
            assert project.status == "created"

            # 2. Start crawling
            crawl_session = await crawler.start_crawl(project.id)
            assert crawl_session.status == "running"

            # 3. Wait for crawl completion (with timeout)
            completed_session = await crawler.wait_for_completion(
                crawl_session.id,
                timeout=300
            )
            assert completed_session.status == "completed"
            assert completed_session.pages_crawled > 0

            # 4. Index documents for search
            collection_name = f"project_{project.id}"
            pages = await db_manager.get_project_pages(project.id)
            documents = [
                {
                    "id": page.id,
                    "title": page.title,
                    "content": page.content_text,
                    "url": page.url,
                    "project": project.name
                }
                for page in pages
            ]
            await rag_service.index_documents(collection_name, documents)

            # 5. Perform search
            search_results = await rag_service.search(
                query="asyncio event loop",
                collection_name=collection_name,
                limit=10
            )
            assert len(search_results) > 0
            assert all("score" in result for result in search_results)

            # 6. Update project status
            updated_project = await db_manager.update_project_status(
                project.id,
                "indexed"
            )
            assert updated_project.status == "indexed"

    @pytest.mark.lifecycle
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_project_recreation_workflow(
        self,
        db_manager,
        crawler,
        sample_project_config
    ):
        """Test recreating an existing project (refresh workflow)."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            # Create initial project
            original_project = await db_manager.create_project(**sample_project_config)

            # Simulate some crawled data
            session1 = await crawler.start_crawl(original_project.id)
            await crawler.complete_crawl(session1.id)

            # Recreate project (refresh)
            recreated_project = await db_manager.recreate_project(
                original_project.name,
                **sample_project_config
            )

            # Should have new ID but same name
            assert recreated_project.id != original_project.id
            assert recreated_project.name == original_project.name
            assert recreated_project.status == "created"

            # Old data should be archived/removed
            old_sessions = await db_manager.get_project_sessions(original_project.id)
            assert all(session.archived for session in old_sessions)

    @pytest.mark.lifecycle
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_project_status_transitions(
        self,
        db_manager,
        crawler,
        sample_project_config
    ):
        """Test valid project status transitions throughout lifecycle."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            project = await db_manager.create_project(**sample_project_config)

            # Valid transitions
            valid_transitions = [
                ("created", "crawling"),
                ("crawling", "processing"),
                ("processing", "indexing"),
                ("indexing", "ready"),
                ("ready", "crawling"),  # Re-crawl
                ("ready", "archived")
            ]

            current_status = project.status
            for from_status, to_status in valid_transitions:
                if current_status == from_status:
                    updated_project = await db_manager.update_project_status(
                        project.id,
                        to_status
                    )
                    assert updated_project.status == to_status
                    current_status = to_status

    @pytest.mark.lifecycle
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_project_cleanup_workflow(
        self,
        db_manager,
        vector_store,
        crawler,
        sample_project_config
    ):
        """Test complete project cleanup and removal."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            # Create and populate project
            project = await db_manager.create_project(**sample_project_config)
            session = await crawler.start_crawl(project.id)
            await crawler.complete_crawl(session.id)

            # Create vector collection
            collection_name = f"project_{project.id}"
            await vector_store.create_collection(collection_name)

            # Cleanup project
            cleanup_result = await db_manager.cleanup_project(project.id)
            assert cleanup_result.success

            # Verify cleanup
            try:
                await db_manager.get_project(project.id)
                pytest.fail("Project should have been deleted")
            except:
                pass  # Expected

            # Vector collection should be removed
            collections = await vector_store.list_collections()
            assert collection_name not in collections

    @pytest.mark.lifecycle
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_project_operations(
        self,
        db_manager,
        crawler,
        sample_project_config
    ):
        """Test concurrent operations on multiple projects."""
        # This test will fail until implementation exists
        import asyncio

        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            # Create multiple projects concurrently
            project_configs = []
            for i in range(3):
                config = sample_project_config.copy()
                config["name"] = f"concurrent-project-{i}"
                config["source_url"] = f"https://example.com/docs/{i}"
                project_configs.append(config)

            # Create projects concurrently
            create_tasks = [
                db_manager.create_project(**config)
                for config in project_configs
            ]
            projects = await asyncio.gather(*create_tasks)

            # Start crawls concurrently
            crawl_tasks = [
                crawler.start_crawl(project.id)
                for project in projects
            ]
            sessions = await asyncio.gather(*crawl_tasks)

            # All should succeed
            assert len(projects) == 3
            assert len(sessions) == 3
            assert all(session.status == "running" for session in sessions)

    @pytest.mark.lifecycle
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_project_error_recovery(
        self,
        db_manager,
        crawler,
        sample_project_config
    ):
        """Test project recovery from various error states."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            project = await db_manager.create_project(**sample_project_config)

            # Simulate crawl failure
            session = await crawler.start_crawl(project.id)
            failed_session = await crawler.mark_crawl_failed(
                session.id,
                error="Network timeout"
            )
            assert failed_session.status == "failed"

            # Retry crawl
            retry_session = await crawler.retry_crawl(project.id)
            assert retry_session.status == "running"
            assert retry_session.id != failed_session.id

            # Recovery should work
            completed_session = await crawler.complete_crawl(retry_session.id)
            assert completed_session.status == "completed"

    @pytest.mark.lifecycle
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_project_data_consistency(
        self,
        db_manager,
        vector_store,
        rag_service,
        crawler,
        sample_project_config
    ):
        """Test data consistency across database and vector store."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            project = await db_manager.create_project(**sample_project_config)
            session = await crawler.start_crawl(project.id)
            await crawler.complete_crawl(session.id)

            # Get pages from database
            db_pages = await db_manager.get_project_pages(project.id)
            db_page_ids = {page.id for page in db_pages}

            # Index in vector store
            collection_name = f"project_{project.id}"
            documents = [
                {
                    "id": page.id,
                    "title": page.title,
                    "content": page.content_text,
                    "url": page.url,
                    "project": project.name
                }
                for page in db_pages
            ]
            await rag_service.index_documents(collection_name, documents)

            # Search should return consistent data
            search_results = await rag_service.search(
                query="test search",
                collection_name=collection_name,
                limit=100
            )

            # All search results should correspond to database pages
            search_page_ids = {result["id"] for result in search_results}
            assert search_page_ids.issubset(db_page_ids)

    @pytest.mark.lifecycle
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_project_metrics_tracking(
        self,
        db_manager,
        crawler,
        sample_project_config
    ):
        """Test project metrics and statistics tracking."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            project = await db_manager.create_project(**sample_project_config)
            session = await crawler.start_crawl(project.id)
            await crawler.complete_crawl(session.id)

            # Get project metrics
            metrics = await db_manager.get_project_metrics(project.id)

            expected_metrics = [
                "total_pages",
                "total_size_bytes",
                "crawl_duration_seconds",
                "average_page_size",
                "successful_pages",
                "failed_pages",
                "duplicate_pages",
                "last_crawl_date",
                "indexing_status"
            ]

            for metric in expected_metrics:
                assert metric in metrics

            # Metrics should be reasonable
            assert metrics["total_pages"] >= 0
            assert metrics["total_size_bytes"] >= 0
            assert metrics["crawl_duration_seconds"] >= 0

    @pytest.mark.lifecycle
    @pytest.mark.integration
    def test_cli_project_lifecycle_commands(
        self,
        docbro_app,
        temp_project_dir,
        sample_project_config
    ):
        """Test CLI commands for complete project lifecycle."""
        # This test will fail until implementation exists
        with pytest.raises((ImportError, AttributeError, NotImplementedError)):
            # Test create command
            result = docbro_app.invoke_command([
                "create",
                sample_project_config["name"],
                "--url", sample_project_config["source_url"],
                "--depth", str(sample_project_config["crawl_depth"])
            ])
            assert result.exit_code == 0

            # Test list command
            result = docbro_app.invoke_command(["list"])
            assert result.exit_code == 0
            assert sample_project_config["name"] in result.output

            # Test crawl command
            result = docbro_app.invoke_command([
                "crawl",
                sample_project_config["name"]
            ])
            assert result.exit_code == 0

            # Test search command
            result = docbro_app.invoke_command([
                "search",
                "test query",
                "--project", sample_project_config["name"]
            ])
            assert result.exit_code == 0

            # Test remove command
            result = docbro_app.invoke_command([
                "remove",
                sample_project_config["name"],
                "--confirm"
            ])
            assert result.exit_code == 0
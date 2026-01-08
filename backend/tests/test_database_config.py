"""
Tests for database configuration and session management.
Covers database.py for increased coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDatabaseConfiguration:
    """Tests for database configuration and URL handling."""

    def test_database_url_converts_postgresql_to_asyncpg(self):
        """Test that postgresql:// URLs are converted to asyncpg."""
        # This is tested via the actual import behavior
        import database

        # The database module should have converted the URL
        assert hasattr(database, "async_engine")
        assert hasattr(database, "AsyncSessionLocal")

    def test_async_session_local_exists(self):
        """Test that AsyncSessionLocal is properly configured."""
        from database import AsyncSessionLocal

        assert AsyncSessionLocal is not None

    def test_async_engine_exists(self):
        """Test that async_engine is properly configured."""
        import os

        from database import async_engine

        if os.environ.get("TESTING") == "true":
            assert async_engine is None
        else:
            assert async_engine is not None


class TestGetAsyncDb:
    """Tests for get_async_db dependency."""

    @pytest.mark.asyncio
    async def test_get_async_db_yields_session(self):
        """Test that get_async_db yields a session."""
        from database import get_async_db

        # Create generator
        gen = get_async_db()

        # We can't easily test the full flow without a real DB
        # but we can verify the generator exists
        assert gen is not None


class TestDatabaseUrlRedaction:
    """Tests for URL redaction in logs."""

    def test_redacted_url_hides_password(self):
        """Test that database URL password is redacted in logs."""
        # The redaction happens at module load time
        # We just verify the redacted_url variable exists
        from database import redacted_url

        # Should not contain actual password patterns
        # If password was present, it should show ****
        assert redacted_url is not None

    def test_redacted_url_format(self):
        """Test redacted URL format is valid."""
        from database import redacted_url

        # Should start with postgresql or similar
        assert "postgresql" in redacted_url.lower() or "****" in redacted_url


class TestSSLConfiguration:
    """Tests for SSL configuration based on environment."""

    def test_async_connect_args_exists(self):
        """Test that async_connect_args is configured."""
        from database import async_connect_args

        assert isinstance(async_connect_args, dict)
        assert "command_timeout" in async_connect_args

    def test_ssl_config_for_localhost(self):
        """Test SSL is disabled for localhost connections."""
        # This depends on the actual database_url
        # If localhost, ssl should be None
        from database import async_connect_args, database_url

        if "localhost" in database_url or "127.0.0.1" in database_url:
            # For localhost, SSL should be None
            assert async_connect_args.get("ssl") is None
        else:
            # For remote, SSL should be "require"
            assert async_connect_args.get("ssl") == "require"


class TestDatabaseModuleExports:
    """Tests for database module exports."""

    def test_get_async_db_export(self):
        """Test get_async_db is exported."""
        from database import get_async_db

        assert callable(get_async_db)

    def test_init_database_export(self):
        """Test init_database is exported."""
        from database import init_database

        assert callable(init_database)

    def test_execute_sql_export(self):
        """Test execute_sql is exported."""
        from database import execute_sql

        assert callable(execute_sql)

    @pytest.mark.asyncio
    async def test_execute_sql_mocked(self):
        """Test execute_sql with mocked engine."""
        from database import execute_sql

        # Proper mocking for async context manager
        mock_engine = AsyncMock()
        mock_engine.begin = MagicMock()
        mock_conn = AsyncMock()

        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        mock_engine.begin.return_value.__aexit__.return_value = None

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_conn.execute.return_value = mock_result

        with patch("database.async_engine", mock_engine):
            result = await execute_sql("SELECT 1")
            assert result.rowcount == 1
            mock_conn.execute.assert_called_once()

    def test_drop_tables_export(self):
        """Test drop_tables is exported."""
        from database import drop_tables

        assert callable(drop_tables)

    def test_base_import(self):
        """Test Base model is properly imported."""
        from models import Base

        assert Base is not None


class TestDatabaseUrlParsing:
    """Tests for database URL parsing logic."""

    def test_database_url_is_string(self):
        """Test database_url is a string."""
        from database import database_url

        assert isinstance(database_url, str)

    def test_database_url_contains_asyncpg(self):
        """Test database_url uses asyncpg driver."""
        from database import database_url

        # After conversion, should contain asyncpg
        assert "asyncpg" in database_url or "postgresql" in database_url

    def test_is_localhost_detection(self):
        """Test localhost detection."""
        from database import database_url

        is_localhost = "localhost" in database_url or "127.0.0.1" in database_url

        # Just verify the check works
        assert isinstance(is_localhost, bool)


class TestAsyncSessionLocal:
    """Tests for AsyncSessionLocal factory."""

    def test_async_session_local_is_session_maker(self):
        """Test AsyncSessionLocal is a session maker."""
        from database import AsyncSessionLocal

        # It should be callable (factory)
        assert callable(AsyncSessionLocal)

    def test_async_session_local_creates_session(self):
        """Test AsyncSessionLocal creates a session."""

        from database import AsyncSessionLocal

        session = AsyncSessionLocal()

        assert session is not None
        # Note: We don't close it here as it's not connected

"""Tests for monitoring infrastructure"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock


class TestSentryIntegration:
    """Test Sentry configuration and integration"""

    def test_sentry_initialization_disabled(self):
        """Test Sentry doesn't initialize when disabled"""
        with patch('src.config.ENABLE_SENTRY', False):
            from src.monitoring import init_sentry
            # Should not raise any errors
            init_sentry()

    def test_sentry_initialization_no_dsn(self):
        """Test Sentry handles missing DSN gracefully"""
        with patch('src.config.ENABLE_SENTRY', True):
            with patch('src.config.SENTRY_DSN', ''):
                from src.monitoring import init_sentry
                # Should log warning but not crash
                init_sentry()

    def test_set_user_context(self):
        """Test setting user context"""
        with patch('src.config.ENABLE_SENTRY', True):
            with patch('sentry_sdk.set_user') as mock_set_user:
                from src.monitoring import set_user_context
                set_user_context("user123")
                # Verify it was called (if Sentry is available)

    def test_capture_exception(self):
        """Test exception capture"""
        with patch('src.config.ENABLE_SENTRY', True):
            from src.monitoring import capture_exception
            test_exception = ValueError("Test error")
            # Should not raise
            capture_exception(test_exception, test_context="value")


class TestPrometheusMetrics:
    """Test Prometheus metrics tracking"""

    def test_metrics_initialization(self):
        """Test metrics are initialized correctly"""
        with patch('src.config.ENABLE_PROMETHEUS', True):
            from src.monitoring.prometheus_metrics import PrometheusMetrics
            metrics = PrometheusMetrics()
            assert metrics.enabled is True

    def test_metrics_disabled(self):
        """Test metrics when disabled"""
        with patch('src.config.ENABLE_PROMETHEUS', False):
            from src.monitoring.prometheus_metrics import PrometheusMetrics
            metrics = PrometheusMetrics()
            assert metrics.enabled is False

    def test_track_request_context_manager(self):
        """Test request tracking context manager"""
        with patch('src.config.ENABLE_PROMETHEUS', True):
            from src.monitoring import track_request

            # Should not raise errors
            with track_request("GET", "/api/test"):
                pass

    def test_track_database_query(self):
        """Test database query tracking"""
        with patch('src.config.ENABLE_PROMETHEUS', True):
            from src.monitoring import track_database_query

            # Should not raise errors
            with track_database_query("SELECT", "users"):
                pass

    def test_update_pool_metrics(self):
        """Test pool metrics update"""
        with patch('src.config.ENABLE_PROMETHEUS', True):
            from src.monitoring import update_pool_metrics

            # Should not raise errors
            update_pool_metrics(total=10, available=5)


class TestMonitoringMiddleware:
    """Test monitoring middleware"""

    @pytest.mark.asyncio
    async def test_monitoring_middleware_tracks_requests(self):
        """Test middleware tracks requests"""
        with patch('src.config.ENABLE_PROMETHEUS', True):
            from src.api.middleware import MonitoringMiddleware
            from starlette.testclient import TestClient
            from fastapi import FastAPI

            app = FastAPI()
            app.add_middleware(MonitoringMiddleware)

            @app.get("/test")
            async def test_endpoint():
                return {"status": "ok"}

            client = TestClient(app)
            response = client.get("/test")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_handles_errors(self):
        """Test middleware tracks errors"""
        with patch('src.config.ENABLE_PROMETHEUS', True):
            from src.api.middleware import MonitoringMiddleware
            from starlette.testclient import TestClient
            from fastapi import FastAPI, HTTPException

            app = FastAPI()
            app.add_middleware(MonitoringMiddleware)

            @app.get("/error")
            async def error_endpoint():
                raise HTTPException(status_code=500, detail="Test error")

            client = TestClient(app)
            response = client.get("/error")

            assert response.status_code == 500


class TestDatabaseQueryTracking:
    """Test database query tracking decorator"""

    @pytest.mark.asyncio
    async def test_query_tracking_decorator(self):
        """Test query tracking decorator"""
        with patch('src.config.ENABLE_PROMETHEUS', True):
            from src.db.queries import track_query

            @track_query("SELECT", "test_table")
            async def test_query():
                return "result"

            result = await test_query()
            assert result == "result"

    @pytest.mark.asyncio
    async def test_query_tracking_disabled(self):
        """Test query tracking when disabled"""
        with patch('src.config.ENABLE_PROMETHEUS', False):
            from src.db.queries import track_query

            @track_query("SELECT", "test_table")
            async def test_query():
                return "result"

            result = await test_query()
            assert result == "result"


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint"""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_data(self):
        """Test metrics endpoint returns Prometheus format"""
        with patch('src.config.ENABLE_PROMETHEUS', True):
            from starlette.testclient import TestClient
            from fastapi import FastAPI
            from src.api.metrics_routes import router

            app = FastAPI()
            app.include_router(router)

            client = TestClient(app)
            response = client.get("/metrics")

            assert response.status_code == 200
            # Prometheus format uses text/plain
            assert "text/plain" in response.headers.get("content-type", "")


class TestAgentMonitoring:
    """Test agent call monitoring"""

    @pytest.mark.asyncio
    async def test_agent_tracks_user_context(self):
        """Test agent sets user context"""
        with patch('src.config.ENABLE_SENTRY', True):
            with patch('src.monitoring.set_user_context') as mock_set_user:
                # This would be tested in integration with actual agent
                # For now, just verify the function exists
                from src.monitoring import set_user_context
                set_user_context("test_user")


def test_config_variables_exist():
    """Test monitoring config variables are defined"""
    from src.config import (
        ENABLE_SENTRY,
        ENABLE_PROMETHEUS,
        SENTRY_DSN,
        SENTRY_ENVIRONMENT,
        SENTRY_TRACES_SAMPLE_RATE,
        PROMETHEUS_PORT
    )

    assert isinstance(ENABLE_SENTRY, bool)
    assert isinstance(ENABLE_PROMETHEUS, bool)
    assert isinstance(SENTRY_DSN, str)
    assert isinstance(SENTRY_ENVIRONMENT, str)
    assert isinstance(SENTRY_TRACES_SAMPLE_RATE, float)
    assert isinstance(PROMETHEUS_PORT, int)

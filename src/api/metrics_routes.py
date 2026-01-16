"""Prometheus metrics endpoint"""
import logging
from fastapi import APIRouter
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics"""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    except ImportError:
        logger.error("prometheus-client not installed")
        return Response(
            content="Prometheus metrics not available",
            status_code=503
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        return Response(
            content=f"Error generating metrics: {str(e)}",
            status_code=500
        )

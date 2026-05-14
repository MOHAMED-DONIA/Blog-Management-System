"""
Monitoring Routes
Provides:
  GET /metrics          — JSON metrics snapshot (Admin only)
  GET /metrics/cache    — Cache statistics
  DELETE /metrics/cache — Clear all caches (Admin only)
  GET /dashboard        — HTML monitoring dashboard (Admin only)
"""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.cache import comments_cache, posts_cache
from app.core.dependencies import require_admin
from app.core.metrics import metrics
from app.models.user import User

router = APIRouter(prefix="/metrics", tags=["Monitoring"])


@router.get("/", response_class=JSONResponse)
def get_metrics(_: User = Depends(require_admin)):
    """Admin only: full application metrics snapshot."""
    return metrics.snapshot()


@router.get("/cache", response_class=JSONResponse)
def get_cache_stats(_: User = Depends(require_admin)):
    """Admin only: cache statistics for posts and comments caches."""
    return {
        "posts_cache": posts_cache.stats(),
        "comments_cache": comments_cache.stats(),
    }


@router.delete("/cache", response_class=JSONResponse)
def clear_all_caches(_: User = Depends(require_admin)):
    """Admin only: flush all caches immediately."""
    posts_cleared = len(posts_cache._store)
    comments_cleared = len(comments_cache._store)
    posts_cache.clear()
    comments_cache.clear()
    return {
        "message": "All caches cleared",
        "posts_entries_removed": posts_cleared,
        "comments_entries_removed": comments_cleared,
    }


@router.get("/dashboard", response_class=HTMLResponse)
def monitoring_dashboard(_: User = Depends(require_admin)):
    """Admin only: render the HTML monitoring dashboard."""
    snapshot = metrics.snapshot()
    cache_stats = {
        "posts_cache": posts_cache.stats(),
        "comments_cache": comments_cache.stats(),
    }

    # Pass data as JSON into the HTML template
    import json
    metrics_json = json.dumps(snapshot)
    cache_json = json.dumps(cache_stats)

    with open("frontend/dashboard.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Inject live data into the page
    html = html.replace("__METRICS_DATA__", metrics_json)
    html = html.replace("__CACHE_DATA__", cache_json)
    return HTMLResponse(content=html)

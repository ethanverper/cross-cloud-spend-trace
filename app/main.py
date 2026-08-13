"""cross-cloud-spend-trace API -- Phase 5 pure JSON API.

Serves Phase 3's already-computed analytics output (spend by source/query/
job, anomaly flags, month-end forecast, optimization suggestions) as JSON to
the React dashboard (`frontend/`). Architecture decision (reading cached
Parquet rather than re-running PySpark per request) is logged in
docs/decisions/0006-phase5-dashboard-api-architecture.md and
app/data/loader.py's own docstring.

In production, this process also serves the built frontend's static assets
(`frontend/dist/`) directly via StaticFiles, so the whole app is one
deployable service -- same pattern factor-attribution-lens/app/main.py
established (decision 0018 there). In development the frontend runs its own
Vite dev server and proxies `/api/*` here instead.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.api.routes import router as api_router

app = FastAPI(
    title="cross-cloud-spend-trace API",
    description="Real spend attribution, anomaly, forecast, and optimization data across AWS, Snowflake, and Databricks, as a pure JSON API.",
    version="0.1.0",
)

# Dev-only convenience: the Vite dev server (localhost:5173) calls this API
# directly. Production serves the frontend from this same origin (below),
# so CORS is a no-op there.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str) -> FileResponse:
        """SPA fallback: any path not already matched above (no API route, no
        `/assets/*` file) serves `index.html` so client-side routes resolve
        on a hard refresh or a deep link too, not just in-app navigation."""
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")

from fastapi import FastAPI

from backend.app.api.routers import (
    admin_router,
    admin_ticket_router,
    customer_router,
)


app = FastAPI(title="ResolveAI API", version="0.1.0")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(admin_ticket_router, prefix="/api/v1")
app.include_router(customer_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple liveness response for local and hosted checks."""
    return {"status": "ok"}

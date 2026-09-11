import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database.session import init_db, DB_PATH
from app.api.auth_routes import router as auth_router
from app.api.onboarding_routes import router as onboarding_router
from app.api.dashboard_routes import router as dashboard_router
from app.api.weaver_routes import router as weaver_router
from app.api.production_routes import router as production_router
from app.api.inventory_routes import router as inventory_router
from app.api.sales_routes import router as sales_router
from app.api.report_routes import router as report_router
from app.api.product_routes import router as product_router
from app.api.purchase_routes import router as purchase_router
from app.api.system_routes import router as system_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database schema on startup if database doesn't exist
    if not os.path.exists(DB_PATH):
        print(f"Initializing clean handloom database schema at {DB_PATH}...")
        init_db()
    yield

app = FastAPI(
    title="Karnataka Handloom Cooperative Management Platform",
    description="Multi-Tenant Digital Operating System for Handloom Weavers Cooperative Societies",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(weaver_router, prefix="/api/v1")
app.include_router(production_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(sales_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")
app.include_router(product_router, prefix="/api/v1")
app.include_router(purchase_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")

# Static Assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/health")
def health_check():
    return {"status": "ok", "platform": "Karnataka Handloom Cooperative Platform", "version": "2.0.0"}

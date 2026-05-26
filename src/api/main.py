from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.execution import router as execution_router
from src.api.routes.exchange import router as exchange_router
from src.api.routes.features import router as features_router
from src.api.routes.health import router as health_router
from src.api.routes.inference import router as inference_router
from src.api.routes.market import router as market_router
from src.api.routes.automation import router as automation_router
from src.api.routes.position_manager import router as position_manager_router
from src.api.routes.reconciliation import router as reconciliation_router
from src.api.routes.risk import router as risk_router
from src.api.routes.signals import router as signals_router
from src.api.routes.status import router as status_router
from src.api.routes.strategy import router as strategy_router
from src.core.settings import load_settings
from src.services.live_update_service import LiveUpdateService


app = FastAPI(
    title="Crypto Trading Bot API",
    version="0.1.0",
    description="Backend API for market data, pipeline status, and inference readiness.",
)

_live_update_service = LiveUpdateService(load_settings())

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(status_router)
app.include_router(execution_router)
app.include_router(exchange_router)
app.include_router(market_router)
app.include_router(features_router)
app.include_router(inference_router)
app.include_router(automation_router)
app.include_router(position_manager_router)
app.include_router(reconciliation_router)
app.include_router(signals_router)
app.include_router(strategy_router)
app.include_router(risk_router)


@app.on_event("startup")
async def startup_event() -> None:
    await _live_update_service.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await _live_update_service.stop()

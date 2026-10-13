from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.config import settings
from backend.app.api.routes_market import router as market_router
from backend.app.api.routes_trade import router as trade_router
from backend.app.api.routes_analytics import router as analytics_router
from backend.app.services.auto_trader import auto_trading_bot
from backend.app.core.logger import logger

# Background task for 24/7 automated strategy execution
async def auto_trader_background_loop():
    while True:
        try:
            await auto_trading_bot.run_step()
        except Exception as e:
            logger.error(f"Error in background trader loop: {str(e)}")
        await asyncio.sleep(auto_trading_bot.interval_seconds)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI Automated Trading Platform Backend initialized.")
    logger.info(f"⚙️ Environment: {settings.APP_ENV} | Host: {settings.HOST}:{settings.PORT}")
    logger.info("🔒 Broker Mode: Active (5-Guardrail Risk Manager Protected)")

    # Start 24/7 background trader
    bg_task = asyncio.create_task(auto_trader_background_loop())
    yield
    bg_task.cancel()
    logger.info("🛑 AI Trading Platform Backend shutting down.")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Automated Live Trading Platform API with 100 Real Markets, 40 Strategies & Alpaca Integration",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)
app.include_router(trade_router)
app.include_router(analytics_router)

@app.get("/")
def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "mode": "24_7_LIVE_AUTOMATED_TRADING",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "paper_trading": True,
        "live_trading_enabled": False,
        "auto_trader_running": auto_trading_bot.is_running
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "error": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

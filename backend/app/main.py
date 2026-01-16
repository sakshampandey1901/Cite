"""FastAPI application entry point."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging

from app.core.config import settings
from app.api.routes import router
from app.api.auth import router as auth_router
from app.api.labeling import router as labeling_router
from app.models.database import init_db, engine
from app.core.database import test_database_connection, DatabaseConnectionError, get_connection_info

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Sentry if DSN is provided
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
            profiles_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        )
        logger.info("✅ Sentry initialized successfully")
    except ImportError:
        logger.warning("Sentry SDK not installed. Run: pip install sentry-sdk[fastapi]")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
else:
    logger.info("Sentry monitoring disabled (no SENTRY_DSN configured)")

# Create FastAPI app
app = FastAPI(
    title="Cognitive Assistant API",
    description="AI-powered personal cognitive assistant with RAG",
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """
    Initialize database connection and tables on application startup.
    
    In production, fails fast if database is unreachable.
    In development, logs warnings but allows startup.
    """
    logger.info("Starting database initialization...")
    
    # Test connection first
    logger.info("Testing database connection...")
    success, error_msg = test_database_connection(engine)
    
    if not success:
        error = DatabaseConnectionError(
            f"Database connection failed during startup:\n{error_msg}"
        )
        
        if settings.ENVIRONMENT == "production":
            logger.error("=" * 80)
            logger.error("PRODUCTION: Database connection failed - application will not start")
            logger.error("=" * 80)
            logger.error(str(error))
            logger.error("=" * 80)
            raise error
        else:
            logger.warning("=" * 80)
            logger.warning("DEVELOPMENT: Database connection failed - application will start but DB operations will fail")
            logger.warning("=" * 80)
            logger.warning(str(error))
            logger.warning("=" * 80)
            logger.warning("Fix the connection and restart the application")
            return
    
    # Log connection info
    conn_info = get_connection_info(engine)
    logger.info(f"Database connection verified: {conn_info.get('url_masked', 'N/A')}")
    
    # Initialize tables
    try:
        init_db()
        logger.info("✅ Database initialization completed successfully")
    except DatabaseConnectionError as e:
        if settings.ENVIRONMENT == "production":
            logger.error(f"Database initialization failed in production: {e}")
            raise
        else:
            logger.warning(f"Database initialization failed (non-production): {e}")
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}", exc_info=True)
        if settings.ENVIRONMENT == "production":
            raise

# CORS middleware - configured for production and development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing."""
    start_time = time.time()

    # Log request
    logger.info(f"{request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Log response time
    process_time = time.time() - start_time
    logger.info(f"Completed in {process_time:.3f}s - Status {response.status_code}")

    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include API routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(router, prefix="/api/v1")
app.include_router(labeling_router, prefix="/api/v1/labeling", tags=["labeling"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Cognitive Assistant API",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )

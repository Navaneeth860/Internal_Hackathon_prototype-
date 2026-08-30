import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.api.endpoints import router as api_router
from backend.app.database import Base, engine
import backend.app.models  # Register models

# Initialize database tables on application startup
Base.metadata.create_all(bind=engine)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="Intelligent Land Record Digitalisation & Validation API",
    description="Thin API wrapping the OCR processing, validation, and human-in-the-loop verification pipeline.",
    version="1.0.0"
)

# CORS Configuration for React Frontend
origins = [
    "http://localhost:5173",  # Vite standard React port
    "http://localhost:3000"   # Create-React-App standard React port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the data directory statically
app.mount("/data", StaticFiles(directory="data"), name="data")

# Register endpoints at the root path to map exactly to GET /health, POST /documents/...
app.include_router(api_router)

logger.info("FastAPI backend initialized successfully with CORS enabled and /data static files mounted.")

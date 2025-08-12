from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
from app.services.api_services import ApiService
from app.logging.logger import Logger
from app.api.user_endpoints import router as user_router
from app.data_modals import User
from app.utils.auth_utils import authenticate_user, get_user_by_username
from pydantic import BaseModel
import uvicorn

# Initialize logger and API service
logger = Logger()
api_service = ApiService()

# Create FastAPI app
app = FastAPI(
    title="Vidhan Bhavan API",
    description="API for accessing Vidhan Bhavan parliamentary data including sessions, debates, members, and resolutions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default port
        "http://localhost:5173",  # Vite default port
        "http://localhost:8080",  # Your current port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://103.112.121.174:8020",  # Public IP and port for deployed frontend
        "*"  # Allow all origins for development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include user authentication routes
app.include_router(user_router)

# ==================== STARTUP HOOK ====================

@app.on_event("startup")
def startup_create_tables() -> None:
    """Ensure all PostgreSQL tables exist on service startup."""
    try:
        from app.database.db_init_postgresql import createtables
        createtables()
        logger.info("✅ Database tables ensured on startup")
    except Exception as e:
        logger.error(f"❌ Failed to create tables on startup: {str(e)}")

# ==================== USER AUTHENTICATION ENDPOINTS ====================

# Pydantic models for login
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    user_id: str
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    message: str

@app.post("/api/login", response_model=LoginResponse)
async def login_user(login_data: LoginRequest):
    """
    Authenticate user and return user data
    """
    try:
        # Get database session
        from app.database.db_conn_postgresql import get_db
        db = next(get_db())
        
        # Authenticate user
        user = authenticate_user(db, login_data.username, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        
        # Return user data
        return {
            "user_id": str(user.user_id),
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
            "message": "Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in login endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.get("/api/user/{username}")
async def get_user_info(username: str):
    """
    Get user information by username
    """
    try:
        # Get database session
        from app.database.db_conn_postgresql import get_db
        db = next(get_db())
        
        # Get user by username
        user = get_user_by_username(db, username)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Return user data
        return {
            "user_id": str(user.user_id),
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
            "department": user.department,
            "position": user.position
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in get_user_info endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

# ==================== ROOT ENDPOINT ====================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Vidhan Bhavan API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "sessions": "/api/sessions",
            "members": "/api/members", 
            "kramanks": "/api/kramanks",
            "debates": "/api/debates",
            "resolutions": "/api/resolutions",
            "search": "/api/search",
            "statistics": "/api/statistics",
            "users": "/api/users",
            "login": "/api/login"
        }
    }

# Simple health endpoint for container healthchecks
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}

# ==================== SESSION ENDPOINTS ====================

@app.get("/api/sessions")
async def get_all_sessions():
    """Get all sessions with summary statistics"""
    try:
        result = api_service.get_all_sessions()
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_all_sessions endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/sessions/{session_id}")
async def get_session_by_id(session_id: str = Path(..., description="Session ID")):
    """Get session by ID with complete details"""
    try:
        result = api_service.get_session_by_id(session_id)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_session_by_id endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/sessions/year/{year}")
async def get_sessions_by_year(year: str = Path(..., description="Year to filter sessions")):
    """Get all sessions for a specific year"""
    try:
        result = api_service.get_sessions_by_year(year)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_sessions_by_year endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/sessions/{session_id}/complete")
async def get_complete_session_data(session_id: str = Path(..., description="Session ID")):
    """Get complete session data including kramanks and debates"""
    try:
        result = api_service.get_complete_session_data(session_id)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_complete_session_data endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== MEMBER ENDPOINTS ====================

@app.get("/api/members")
async def get_all_members():
    """Get all members with summary statistics"""
    try:
        result = api_service.get_all_members()
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_all_members endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/sessions/{session_id}/members")
async def get_members_by_session(session_id: str = Path(..., description="Session ID")):
    """Get all members for a specific session"""
    try:
        result = api_service.get_members_by_session(session_id)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_members_by_session endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== KRAMANK ENDPOINTS ====================

@app.get("/api/kramanks")
async def get_all_kramanks():
    """Get all kramanks with summary statistics"""
    try:
        result = api_service.get_all_kramanks()
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_all_kramanks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/sessions/{session_id}/kramanks")
async def get_kramanks_by_session_id(session_id: str = Path(..., description="Session ID")):
    """Get all kramanks for a specific session ID"""
    try:
        result = api_service.get_kramanks_by_session_id(session_id)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_kramanks_by_session_id endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/kramanks/{kramank_id}")
async def get_kramank_with_debates(kramank_id: str = Path(..., description="Kramank ID")):
    """Get complete kramank data including debates"""
    try:
        result = api_service.get_kramank_with_debates(kramank_id)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_kramank_with_debates endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== DEBATE ENDPOINTS ====================

@app.get("/api/debates")
async def get_all_debates():
    """Get all debates with summary statistics"""
    try:
        result = api_service.get_all_debates()
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_all_debates endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/kramanks/{kramank_id}/debates")
async def get_debates_by_kramank_id(kramank_id: str = Path(..., description="Kramank ID")):
    """Get all debates for a specific kramank ID"""
    try:
        result = api_service.get_debates_by_kramank_id(kramank_id)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_debates_by_kramank_id endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/debates/search")
async def get_debates_by_topic(
    topic: str = Query(..., description="Topic to search for (partial match)")
):
    """Get debates by topic (partial match)"""
    try:
        result = api_service.get_debates_by_topic(topic)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_debates_by_topic endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/debates/lob-type/{lob_type}")
async def get_debates_by_lob_type(lob_type: str = Path(..., description="LOB type to filter by")):
    """Get debates by LOB type"""
    try:
        result = api_service.get_debates_by_lob_type(lob_type)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_debates_by_lob_type endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== RESOLUTION ENDPOINTS ====================

@app.get("/api/resolutions")
async def get_all_resolutions():
    """Get all resolutions with summary statistics"""
    try:
        result = api_service.get_all_resolutions()
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_all_resolutions endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/sessions/{session_id}/resolutions")
async def get_resolutions_by_session(session_id: str = Path(..., description="Session ID")):
    """Get all resolutions for a specific session"""
    try:
        result = api_service.get_resolutions_by_session(session_id)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_resolutions_by_session endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== SEARCH AND ANALYTICS ENDPOINTS ====================

@app.get("/api/search/debates")
async def search_debates(
    query: str = Query(..., description="Search query for debates"),
    limit: int = Query(50, description="Maximum number of results to return", ge=1, le=100)
):
    """Search debates by topic or text content"""
    try:
        result = api_service.search_debates(query, limit)
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in search_debates endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/statistics")
async def get_database_statistics():
    """Get comprehensive database statistics"""
    try:
        result = api_service.get_database_statistics()
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_database_statistics endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== HEALTH CHECK ENDPOINT ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connectivity by getting basic statistics
        result = api_service.get_database_statistics()
        if result["success"]:
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": result["data"]["last_updated"]
            }
        else:
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": result["error"]
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e)
        }

# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "Resource not found",
            "message": "The requested resource was not found on this server"
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )

# ==================== STARTUP AND SHUTDOWN EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 Vidhan Bhavan API starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("🛑 Vidhan Bhavan API shutting down...")

# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    uvicorn.run(
        "app.api.api_file:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

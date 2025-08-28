from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import os
import json
import uuid
from typing import Optional, List
from app.services.api_services import ApiService
from app.logging.logger import Logger
from sqlalchemy import text
from app.api.user_endpoints import router as user_router
from app.data_modals import User
from app.utils.auth_utils import authenticate_user, get_user_by_username
from pydantic import BaseModel
from app.database.db_conn_postgresql import get_db
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
        logger.info(f"Login request received for user: {login_data.username}")
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

@app.get("/api/sessions/{session_id}/active-kramanks")
async def get_active_kramanks_by_session(session_id: str = Path(..., description="Session ID")):
    """Get all kramanks for a session that have active debates"""
    try:
        db = next(get_db())
        
        # Get kramanks that have at least one active debate
        query = text("""
            SELECT DISTINCT k.* 
            FROM kramanks k
            INNER JOIN debates d ON k.kramank_id = d.kramank_id
            WHERE k.session_id = :session_id
            AND (d.status = 'active' OR d.status IS NULL)
            ORDER BY k.number
        """)
        
        result = db.execute(query, {"session_id": session_id}).fetchall()
        
        if not result:
            return JSONResponse(content={
                "success": True,
                "data": {
                    "kramanks": [],
                    "count": 0
                }
            })
            
        kramanks = [{
            "kramank_id": str(row.kramank_id),
            "number": row.number,
            "date": row.date,
            "chairman": row.chairman,
            "vol": row.vol
        } for row in result]
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "kramanks": kramanks,
                "count": len(kramanks)
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting active kramanks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

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

# ==================== PDF ENDPOINTS ====================

@app.get("/api/pdf/{kramank_id}/{document_name}")
async def get_pdf_file(kramank_id: str = Path(..., description="Kramank ID"), 
                      document_name: str = Path(..., description="PDF document name")):
    """Serve PDF files from the generated_pdfs directory with kramank_id subfolder structure"""
    try:
        # Define the base directory for PDFs with kramank_id subfolder
        pdf_dir = os.path.join(os.getcwd(), "generated_pdfs", kramank_id)
        pdf_path = os.path.join(pdf_dir, document_name)
        
        logger.info(f"🔍 Looking for PDF at: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            logger.error(f"❌ PDF file not found at: {pdf_path}")
            raise HTTPException(status_code=404, detail="PDF file not found")
            
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=document_name
        )
    except Exception as e:
        logger.error(f"❌ Error serving PDF file: {str(e)}")
        raise HTTPException(status_code=500, detail="Error serving PDF file")

# ==================== DEBATE ENDPOINTS ====================

@app.get("/api/debates/{debate_id}/adjacent")
async def get_adjacent_debates(debate_id: str = Path(..., description="Debate ID")):
    """Get previous and next debates from the same kramank"""
    try:
        db = next(get_db())
        
        # Get current debate to get kramank_id and sequence info
        current_debate = db.execute(
            text("""
                SELECT * FROM debates 
                WHERE debate_id = :debate_id 
                AND (status = 'active' OR status IS NULL)
            """),
            {"debate_id": debate_id}
        ).first()
        
        if not current_debate:
            raise HTTPException(status_code=404, detail="Debate not found")
            
        # Get adjacent debates (previous and next) from same kramank
        adjacent = db.execute(
            text("""
                SELECT debate_id, topic, text, sequence_number,
                       CASE 
                           WHEN sequence_number < :current_seq THEN 'previous'
                           ELSE 'next'
                       END as position
                FROM debates 
                WHERE kramank_id = :kramank_id 
                AND debate_id != :debate_id
                AND (status = 'active' OR status IS NULL)
                AND (
                    sequence_number = :current_seq - 1  -- Previous debate
                    OR sequence_number = :current_seq + 1  -- Next debate
                )
                ORDER BY sequence_number
            """),
            {
                "kramank_id": current_debate.kramank_id,
                "debate_id": debate_id,
                "current_seq": current_debate.sequence_number
            }
        ).fetchall()
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "adjacent_debates": [
                    {
                        "id": str(row.debate_id),
                        "topic": row.topic,
                        "preview": row.text[:200] + "..." if len(row.text) > 200 else row.text,
                        "position": row.position,  # 'previous' or 'next'
                        "sequence_number": row.sequence_number
                    }
                    for row in adjacent
                ]
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting adjacent debates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.get("/api/debates/next/{sequence_number}")
async def get_next_debate(sequence_number: int = Path(..., description="Current sequence number")):
    """Get the next debate by sequence number"""
    try:
        db = next(get_db())
        
        # First, get the current debate to find its kramank_id
        current_debate = db.execute(
            text("""
                SELECT kramank_id
                FROM debates 
                WHERE sequence_number = :seq
                AND (status = 'active' OR status IS NULL)
            """),
            {"seq": sequence_number}
        ).first()
        
        if not current_debate:
            return JSONResponse(content={
                "success": True,
                "data": {
                    "debate": None
                }
            })
        
        # Get the next debate with sequence_number + 1 from the same kramank
        next_debate = db.execute(
            text("""
                SELECT debate_id, topic, text, sequence_number, kramank_id
                FROM debates 
                WHERE sequence_number = :next_seq
                AND kramank_id = :kramank_id
                AND (status = 'active' OR status IS NULL)
            """),
            {
                "next_seq": sequence_number + 1,
                "kramank_id": current_debate.kramank_id
            }
        ).first()
        
        # If no exact match, find the next available debate from the same kramank
        if not next_debate:
            next_debate = db.execute(
                text("""
                    SELECT debate_id, topic, text, sequence_number, kramank_id
                    FROM debates 
                    WHERE sequence_number > :current_seq
                    AND kramank_id = :kramank_id
                    AND (status = 'active' OR status IS NULL)
                    ORDER BY sequence_number
                    LIMIT 1
                """),
                {
                    "current_seq": sequence_number,
                    "kramank_id": current_debate.kramank_id
                }
            ).first()
        
        if not next_debate:
            return JSONResponse(content={
                "success": True,
                "data": {
                    "debate": None
                }
            })
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "debate": {
                    "id": str(next_debate.debate_id),
                    "topic": next_debate.topic,
                    "preview": next_debate.text[:200] + "..." if len(next_debate.text) > 200 else next_debate.text,
                    "sequence_number": next_debate.sequence_number
                }
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting next debate: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.post("/api/debates/{primary_id}/merge/{secondary_id}")
async def merge_debates(
    primary_id: str = Path(..., description="Primary debate ID to keep"),
    secondary_id: str = Path(..., description="Secondary debate ID to merge and soft delete")
):
    """Merge two debates, keeping the primary and soft deleting the secondary"""
    try:
        db = next(get_db())
        
        # Get both debates
        primary = db.execute(
            text("SELECT * FROM debates WHERE debate_id = :id"),
            {"id": primary_id}
        ).first()
        
        secondary = db.execute(
            text("SELECT * FROM debates WHERE debate_id = :id"),
            {"id": secondary_id}
        ).first()
        
        if not primary or not secondary:
            raise HTTPException(status_code=404, detail="One or both debates not found")
            
        # Ensure debates are adjacent and from the same kramank
        if primary.kramank_id != secondary.kramank_id:
            raise HTTPException(status_code=400, detail="Can only merge debates from the same kramank")
            
        if abs(primary.sequence_number - secondary.sequence_number) != 1:
            raise HTTPException(status_code=400, detail="Can only merge adjacent debates")
            
        # Ensure both debates are active
        if primary.status != 'active' or secondary.status != 'active':
            raise HTTPException(status_code=400, detail="Can only merge active debates")
            
        # Combine texts
        combined_text = f"{primary.text}\n{secondary.text}"
        
        # Update primary debate
        db.execute(
            text("""
                UPDATE debates 
                SET text = :text,
                    last_update = TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
                WHERE debate_id = :id
            """),
            {"id": primary_id, "text": combined_text}
        )
        
        # Soft delete secondary debate
        db.execute(
            text("""
                UPDATE debates 
                SET status = 'deleted',
                    last_update = TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
                WHERE debate_id = :id
            """),
            {"id": secondary_id}
        )
        
       
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": "Debates merged successfully",
            "data": {
                "primary_id": str(primary_id),
                "secondary_id": str(secondary_id)
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error merging debates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.post("/api/debates/fix-sequence-numbers/{kramank_id}")
async def fix_sequence_numbers(kramank_id: str = Path(..., description="Kramank ID to fix sequence numbers for")):
    """Fix sequence numbers for a kramank to ensure they are consecutive"""
    try:
        db = next(get_db())
        
        # Get all active debates for the kramank ordered by current sequence number
        debates = db.execute(
            text("""
                SELECT debate_id, sequence_number
                FROM debates
                WHERE kramank_id = :kramank_id
                AND status = 'active'
                ORDER BY sequence_number
            """),
            {"kramank_id": kramank_id}
        ).fetchall()
        
        if not debates:
            return JSONResponse(content={
                "success": True,
                "message": f"No active debates found for kramank {kramank_id}",
                "data": {"fixed_count": 0}
            })
        
        # Check if sequence numbers are already consecutive starting from 1
        needs_fixing = False
        for i, debate in enumerate(debates):
            if debate.sequence_number != i + 1:
                needs_fixing = True
                break
        
        if not needs_fixing:
            return JSONResponse(content={
                "success": True,
                "message": f"Sequence numbers are already correct for kramank {kramank_id}",
                "data": {"fixed_count": 0}
            })
        
        # Fix sequence numbers to be consecutive starting from 1
        fixed_count = 0
        for i, debate in enumerate(debates):
            new_sequence = i + 1
            if debate.sequence_number != new_sequence:
                db.execute(
                    text("""
                        UPDATE debates
                        SET sequence_number = :new_seq,
                            last_update = TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
                        WHERE debate_id = :debate_id
                    """),
                    {
                        "debate_id": debate.debate_id,
                        "new_seq": new_sequence
                    }
                )
                fixed_count += 1
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Fixed sequence numbers for kramank {kramank_id}",
            "data": {
                "kramank_id": kramank_id,
                "total_debates": len(debates),
                "fixed_count": fixed_count
            }
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error fixing sequence numbers: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.get("/api/debates/{debate_id}")
async def get_debate_by_id(debate_id: str = Path(..., description="Debate ID")):
    """Get debate by ID with complete details"""
    try:
        db = next(get_db())
        logger.info(f"debate id from ui: {debate_id}")
        query = text("""
            SELECT * FROM debates 
            WHERE debate_id = :debate_id 
            AND (status = 'active' OR status IS NULL)
        """)
        result = db.execute(query, {"debate_id": debate_id}).first()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Debate not found: {debate_id}")
            
        # Convert row to dict and handle UUID serialization
        debate = {}
        for key, value in result._mapping.items():
            # Convert UUID to string
            if isinstance(value, uuid.UUID):
                debate[key] = str(value)
            else:
                debate[key] = value
        
        # Parse JSON fields
        for field in ['question_number', 'members', 'topics', 'answers_by']:
            if field in debate and debate[field]:
                try:
                    debate[field] = json.loads(debate[field])
                except:
                    pass
                    
        return JSONResponse(content=debate, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in get_debate_by_id endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

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

@app.get("/api/kramanks/{kramank_id}/active-debates")
async def get_active_debates_by_kramank(kramank_id: str = Path(..., description="Kramank ID")):
    """Get all active debates for a specific kramank ID"""
    try:
        db = next(get_db())
        
        # Get active debates for the kramank
        query = text("""
            SELECT * FROM debates 
            WHERE kramank_id = :kramank_id 
            AND (status = 'active' OR status IS NULL)
            ORDER BY sequence_number
        """)
        
        result = db.execute(query, {"kramank_id": kramank_id}).fetchall()
        
        if not result:
            return JSONResponse(content={
                "success": True,
                "data": {
                    "debates": [],
                    "count": 0
                }
            })
            
        debates = []
        for row in result:
            debate = {}
            for key, value in row._mapping.items():
                # Convert UUID to string
                if isinstance(value, uuid.UUID):
                    debate[key] = str(value)
                else:
                    debate[key] = value
            debates.append(debate)
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "debates": debates,
                "count": len(debates)
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting active debates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

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

@app.delete("/api/debates/{debate_id}")
async def delete_debate(debate_id: str = Path(..., description="Debate ID to soft delete")):
    """Soft delete a debate by setting its status to 'deleted'"""
    try:
        db = next(get_db())
        try:
            # Update debate status to 'deleted'
            query = text("""
                UPDATE debates 
                SET status = 'deleted' 
                WHERE debate_id = :debate_id
                RETURNING debate_id
            """)
            result = db.execute(query, {"debate_id": debate_id}).first()
            
            if not result:
                raise HTTPException(status_code=404, detail=f"Debate not found: {debate_id}")
                
            db.commit()
            logger.info(f"✅ Successfully soft deleted debate {debate_id}")
            
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Debate {debate_id} has been deleted",
                    "debate_id": str(result[0])
                },
                status_code=200
            )
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error soft deleting debate {debate_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error in delete_debate endpoint: {str(e)}")
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

@app.get("/api/stats")
async def get_stats():
    """Get basic statistics for the frontend dashboard"""
    try:
        result = api_service.get_database_statistics()
        if result["success"]:
            stats = result["data"]["statistics"]
            return {
                "sessions_count": stats.get("sessions", 0),
                "debates_count": stats.get("debates", 0)
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])
    except Exception as e:
        logger.error(f"❌ Error in get_stats endpoint: {str(e)}")
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

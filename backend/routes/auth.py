"""
Authentication routes - Google OAuth2
"""

import os
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import datetime,timezone
from database import get_db
from auth_utils import create_access_token
from models import TokenResponse, UserResponse

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@router.get("/google")
async def google_auth():

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500, 
            detail="Google OAuth not configured. Please set GOOGLE_CLIENT_ID in .env"
        )
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{query_string}")


@router.get("/google/callback")
async def google_callback(code: str = None, error: str = None):
    """Handle Google OAuth callback"""
    if error:
        return RedirectResponse(url=f"/login?error={error}")
    
    if not code:
        return RedirectResponse(url="/login?error=no_code")
    

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        
        if token_response.status_code != 200:
            return RedirectResponse(url="/login?error=token_exchange_failed")
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        
        user_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_response.status_code != 200:
            return RedirectResponse(url="/login?error=userinfo_failed")
        
        google_user = user_response.json()
    
    db = get_db()
    existing_user = await db.users.find_one({"email": google_user["email"]})
    
    if existing_user:

        await db.users.update_one(
            {"_id": existing_user["_id"]},
            {"$set": {"last_login": datetime.now(timezone.utc), "picture": google_user.get("picture")}}
        )
        user_id = str(existing_user["_id"])
    else:

        new_user = {
            "email": google_user["email"],
            "name": google_user.get("name", ""),
            "picture": google_user.get("picture", ""),
            "google_id": google_user.get("sub", ""),
            "created_at": datetime.now(timezone.utc),
            "last_login": datetime.now(timezone.utc),
            "streak": 0,
            "last_entry_date": None,
            "total_entries": 0
        }
        result = await db.users.insert_one(new_user)
        user_id = str(result.inserted_id)
    
    jwt_token = create_access_token(user_id, google_user["email"])
    
  
    return RedirectResponse(url=f"/dashboard?token={jwt_token}")


@router.get("/me")
async def get_me(request: Request):

    from auth_utils import get_current_user
    from fastapi.security import HTTPAuthorizationCredentials
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    from auth_utils import decode_token
    from database import get_db
    from bson import ObjectId
    
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture", ""),
        "streak": user.get("streak", 0),
        "total_entries": user.get("total_entries", 0),
        "created_at": user["created_at"].isoformat()
    }


@router.post("/logout")
async def logout():

    return {"message": "Logged out successfully"}
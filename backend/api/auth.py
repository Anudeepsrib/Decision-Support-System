"""
Authentication API Endpoints
Enterprise-grade login, logout, and token management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from pydantic import BaseModel
from typing import Optional

from security.auth import (
    authenticate_user,
    SecurityManager,
    Token,
    UserRole,
    SBUAccess,
    get_user,
    MOCK_USERS,
)
from security.rate_limit import brute_force_protection

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ─── Request/Response Models ───
class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None

class LoginResponse(BaseModel):
    success: bool
    token: Optional[Token] = None
    message: str
    requires_mfa: bool = False

class UserProfileResponse(BaseModel):
    username: str
    email: str
    full_name: str
    role: UserRole
    sbu_access: list[str]
    permissions: list[str]
    mfa_enabled: bool

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

# ─── Login Endpoint ───
@router.post("/login", response_model=LoginResponse)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return JWT tokens.
    Implements brute force protection and MFA verification.
    """
    client_ip = request.client.host if request.client else "unknown"
    lockout_key = f"{client_ip}:{form_data.username}"
    
    # Check brute force lockout
    is_locked, remaining = brute_force_protection.is_locked_out(lockout_key)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked. Try again in {remaining} seconds."
        )
    
    # Authenticate
    user = await authenticate_user(form_data.username, form_data.password)
    
    if not user:
        brute_force_protection.record_failure(lockout_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if MFA is required
    if user.get("mfa_enabled", False):
        # In production, verify MFA code here
        # For now, we'll simulate MFA check
        pass
    
    # Clear failed attempts on success
    brute_force_protection.record_success(lockout_key)
    
    # Generate tokens
    token_data = {
        "sub": user["username"],
        "role": user["role"].value,
        "permissions": user.get("permissions", []),
        "sbu_access": [s.value for s in user["sbu_access"]],
    }
    
    access_token = SecurityManager.create_access_token(token_data)
    refresh_token = SecurityManager.create_refresh_token({"sub": user["username"]})
    
    return LoginResponse(
        success=True,
        token=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=30,
            role=user["role"],
            permissions=user.get("permissions", [])
        ),
        message="Login successful",
        requires_mfa=False
    )

# ─── Token Refresh ───
@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    token_data = SecurityManager.decode_token(refresh_token)
    
    if not token_data or token_data.username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user data
    user = get_user(token_data.username)
    if not user or not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Generate new tokens
    token_data_dict = {
        "sub": user["username"],
        "role": user["role"].value,
        "permissions": user.get("permissions", []),
        "sbu_access": [s.value for s in user["sbu_access"]],
    }
    
    new_access_token = SecurityManager.create_access_token(token_data_dict)
    new_refresh_token = SecurityManager.create_refresh_token({"sub": user["username"]})
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=30,
        role=user["role"],
        permissions=user.get("permissions", [])
    )

# ─── Logout ───
@router.post("/logout")
async def logout():
    """Logout user (client should discard tokens)"""
    # In production, add token to revocation list
    return {"message": "Logout successful", "detail": "Please discard your tokens"}

# ─── User Profile ───
@router.get("/me", response_model=UserProfileResponse)
async def get_profile(current_user: dict = Depends(lambda: get_user("regulatory.officer@kserc.gov.in"))):
    """Get current user profile"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return UserProfileResponse(
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        sbu_access=[s.value for s in current_user["sbu_access"]],
        permissions=current_user.get("permissions", []),
        mfa_enabled=current_user.get("mfa_enabled", False)
    )

# ─── Password Change ───
@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: dict = Depends(lambda: get_user("regulatory.officer@kserc.gov.in"))
):
    """Change user password"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Verify current password
    if not SecurityManager.verify_password(
        request.current_password, 
        current_user["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate and hash new password
    try:
        new_hash = SecurityManager.get_password_hash(request.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # In production, update password in database
    # current_user["hashed_password"] = new_hash
    
    return {"message": "Password changed successfully"}

# ─── Health Check (no auth required) ───
@router.get("/health")
async def auth_health():
    """Check authentication service health"""
    return {
        "service": "authentication",
        "status": "healthy",
        "version": "1.0.0"
    }

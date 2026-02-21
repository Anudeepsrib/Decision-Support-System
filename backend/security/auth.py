"""
Enterprise Security Module — RBAC, Authentication & Authorization
Implements enterprise-grade security for the ARR Truing-Up DSS
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os

# ─── Security Configuration ───
SECRET_KEY = os.getenv("SECRET_KEY", "your-256-bit-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# ─── Password Hashing ───
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── Role Definitions ───
class UserRole(str, Enum):
    """Enterprise RBAC Role Hierarchy"""
    SUPER_ADMIN = "super_admin"           # Full system access
    REGULATORY_OFFICER = "regulatory_officer"  # Final approval authority
    SENIOR_AUDITOR = "senior_auditor"     # Review and override AI suggestions
    DATA_ENTRY_AGENT = "data_entry_agent" # Upload documents, trigger AI
    READONLY_ANALYST = "readonly_analyst"  # View reports only
    AUDIT_VIEWER = "audit_viewer"         # View audit trails only

# ─── SBU Access Control ───
class SBUAccess(str, Enum):
    """SBU Data Isolation Levels"""
    SBU_G = "SBU-G"  # Generation
    SBU_T = "SBU-T"  # Transmission
    SBU_D = "SBU-D"  # Distribution
    ALL = "ALL"      # Cross-SBU access (restricted)

# ─── Permission Matrix ───
ROLE_PERMISSIONS: Dict[UserRole, List[str]] = {
    UserRole.SUPER_ADMIN: [
        "*"  # All permissions
    ],
    UserRole.REGULATORY_OFFICER: [
        "mapping.confirm",
        "mapping.override",
        "mapping.reject",
        "reports.generate_final",
        "audit.read",
        "extraction.read",
        "data.read_all_sbus",
        "system.read_config",
    ],
    UserRole.SENIOR_AUDITOR: [
        "mapping.confirm",
        "mapping.override",
        "mapping.reject",
        "reports.generate_draft",
        "audit.read",
        "extraction.read",
        "extraction.upload",
    ],
    UserRole.DATA_ENTRY_AGENT: [
        "extraction.upload",
        "extraction.read_own",
        "mapping.read",
        "reports.read",
    ],
    UserRole.READONLY_ANALYST: [
        "reports.read",
        "extraction.read",
    ],
    UserRole.AUDIT_VIEWER: [
        "audit.read",
    ],
}

# ─── Pydantic Models ───
class UserBase(BaseModel):
    username: str
    email: str
    full_name: str
    role: UserRole
    sbu_access: List[SBUAccess]
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    password_changed_at: datetime
    mfa_enabled: bool = False

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    role: UserRole
    permissions: List[str]

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None
    permissions: List[str] = []
    sbu_access: List[str] = []
    exp: Optional[datetime] = None

# ─── Security Utilities ───
class SecurityManager:
    """Enterprise Security Manager for authentication and authorization"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password for storing"""
        # Enforce strong password policy
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain lowercase letter")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            raise ValueError("Password must contain special character")
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[TokenData]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            role: str = payload.get("role")
            permissions: List[str] = payload.get("permissions", [])
            sbu_access: List[str] = payload.get("sbu_access", [])
            exp = payload.get("exp")
            
            if username is None:
                return None
            
            return TokenData(
                username=username,
                role=UserRole(role) if role else None,
                permissions=permissions,
                sbu_access=sbu_access,
                exp=datetime.fromtimestamp(exp) if exp else None
            )
        except JWTError:
            return None
    
    @staticmethod
    def has_permission(user_role: UserRole, permission: str) -> bool:
        """Check if role has specific permission"""
        permissions = ROLE_PERMISSIONS.get(user_role, [])
        return "*" in permissions or permission in permissions
    
    @staticmethod
    def can_access_sbu(user_sbu_access: List[SBUAccess], target_sbu: str) -> bool:
        """Check if user can access specific SBU data"""
        if SBUAccess.ALL in user_sbu_access:
            return True
        try:
            target = SBUAccess(target_sbu)
            return target in user_sbu_access
        except ValueError:
            return False

# ─── FastAPI Security Dependencies ───
security_bearer = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> TokenData:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    token_data = SecurityManager.decode_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if token_data.exp and token_data.exp < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data

async def require_permission(permission: str):
    """Dependency factory to require specific permission"""
    async def permission_checker(user: TokenData = Depends(get_current_user)):
        if not user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role not found in token"
            )
        
        if not SecurityManager.has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        return user
    return permission_checker

async def require_sbu_access(sbu_code: str):
    """Dependency factory to require SBU access"""
    async def sbu_checker(user: TokenData = Depends(get_current_user)):
        user_sbu_access = [SBUAccess(s) for s in user.sbu_access]
        if not SecurityManager.can_access_sbu(user_sbu_access, sbu_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to SBU: {sbu_code}"
            )
        return user
    return sbu_checker

# ─── Role-specific Dependencies ───
require_regulatory_officer = require_permission("mapping.confirm")
require_senior_auditor = require_permission("mapping.override")
require_data_entry = require_permission("extraction.upload")
require_audit_access = require_permission("audit.read")

# ─── Mock User Database (Production: Use PostgreSQL) ───
# These would be in your actual database
MOCK_USERS = {
    "regulatory.officer@kserc.gov.in": {
        "username": "regulatory.officer@kserc.gov.in",
        "email": "regulatory.officer@kserc.gov.in",
        "full_name": "Senior Regulatory Officer",
        "role": UserRole.REGULATORY_OFFICER,
        "sbu_access": [SBUAccess.ALL],
        "hashed_password": pwd_context.hash("TempPass123!"),  # Change in production
        "is_active": True,
        "mfa_enabled": True,
    },
    "auditor@utility.com": {
        "username": "auditor@utility.com",
        "email": "auditor@utility.com",
        "full_name": "Senior Auditor",
        "role": UserRole.SENIOR_AUDITOR,
        "sbu_access": [SBUAccess.SBU_D],
        "hashed_password": pwd_context.hash("TempPass123!"),
        "is_active": True,
        "mfa_enabled": False,
    },
    "data.entry@utility.com": {
        "username": "data.entry@utility.com",
        "email": "data.entry@utility.com",
        "full_name": "Data Entry Agent",
        "role": UserRole.DATA_ENTRY_AGENT,
        "sbu_access": [SBUAccess.SBU_D],
        "hashed_password": pwd_context.hash("TempPass123!"),
        "is_active": True,
        "mfa_enabled": False,
    },
}

def get_user(username: str) -> Optional[Dict[str, Any]]:
    """Get user from database (mock implementation)"""
    return MOCK_USERS.get(username)

# ─── Login Function ───
async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user and return user data"""
    user = get_user(username)
    if not user:
        return None
    if not user.get("is_active", False):
        return None
    if not SecurityManager.verify_password(password, user["hashed_password"]):
        return None
    return user

"""
Rate Limiting & DDoS Protection Module
Implements enterprise-grade request throttling and abuse prevention
"""

from fastapi import Request, HTTPException, status
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import time
import hashlib

# ─── Rate Limiting Configuration ───
RATE_LIMIT_CONFIG = {
    "default": {"requests": 100, "window": 60},  # 100 requests per minute
    "auth": {"requests": 5, "window": 60},      # 5 login attempts per minute
    "upload": {"requests": 10, "window": 60},    # 10 uploads per minute
    "api": {"requests": 1000, "window": 60},     # 1000 API calls per minute
    "sensitive": {"requests": 10, "window": 60}, # 10 sensitive operations per minute
}

# ─── In-Memory Store (Production: Use Redis) ───
class RateLimitStore:
    """Simple in-memory rate limit store (Production: Use Redis)"""
    
    def __init__(self):
        self._store: Dict[str, Tuple[int, float]] = {}
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int, int]:
        """
        Check if request is allowed
        Returns: (is_allowed, remaining_requests, reset_time)
        """
        now = time.time()
        window_start = now - window_seconds
        
        # Get current count and timestamp
        count, timestamp = self._store.get(key, (0, now))
        
        # Reset if window has passed
        if timestamp < window_start:
            count = 0
            timestamp = now
        
        # Check limit
        if count >= max_requests:
            reset_time = int(timestamp + window_seconds - now)
            return False, 0, max(0, reset_time)
        
        # Increment count
        self._store[key] = (count + 1, timestamp)
        remaining = max_requests - count - 1
        reset_time = int(window_seconds - (now - timestamp))
        
        return True, remaining, reset_time
    
    def get_client_key(self, request: Request, endpoint_type: str = "default") -> str:
        """Generate unique key for client + endpoint type"""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Consider X-Forwarded-For for proxies
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Create unique key
        key_data = f"{client_ip}:{endpoint_type}:{request.url.path}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

# Global rate limit store
rate_limit_store = RateLimitStore()

# ─── Rate Limiting Middleware ───
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on all requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/", "/health"]:
            return await call_next(request)
        
        # Determine endpoint type
        endpoint_type = self._get_endpoint_type(request)
        config = RATE_LIMIT_CONFIG.get(endpoint_type, RATE_LIMIT_CONFIG["default"])
        
        # Check rate limit
        key = rate_limit_store.get_client_key(request, endpoint_type)
        is_allowed, remaining, reset_time = rate_limit_store.is_allowed(
            key, config["requests"], config["window"]
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {reset_time} seconds.",
                headers={
                    "X-RateLimit-Limit": str(config["requests"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(config["requests"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _get_endpoint_type(self, request: Request) -> str:
        """Determine endpoint type for rate limiting"""
        path = request.url.path
        method = request.method
        
        # Auth endpoints
        if "/auth" in path or "/login" in path:
            return "auth"
        
        # Upload endpoints
        if "/upload" in path or "/extract" in path:
            return "upload"
        
        # Sensitive operations
        if method in ["POST", "PUT", "DELETE"] and "/confirm" in path:
            return "sensitive"
        
        # API endpoints
        if "/api" in path or path.startswith("/v"):
            return "api"
        
        return "default"

# ─── Brute Force Protection ───
class BruteForceProtection:
    """Protection against brute force attacks"""
    
    def __init__(self):
        self._failed_attempts: Dict[str, Tuple[int, float]] = {}
        self._lockout_duration = 900  # 15 minutes
        self._max_attempts = 5
    
    def record_failure(self, identifier: str):
        """Record a failed login attempt"""
        now = time.time()
        count, _ = self._failed_attempts.get(identifier, (0, now))
        self._failed_attempts[identifier] = (count + 1, now)
    
    def record_success(self, identifier: str):
        """Clear failed attempts on successful login"""
        if identifier in self._failed_attempts:
            del self._failed_attempts[identifier]
    
    def is_locked_out(self, identifier: str) -> Tuple[bool, int]:
        """Check if identifier is locked out, returns (is_locked, remaining_seconds)"""
        if identifier not in self._failed_attempts:
            return False, 0
        
        count, timestamp = self._failed_attempts[identifier]
        now = time.time()
        
        # Check if lockout period has passed
        if now - timestamp > self._lockout_duration:
            del self._failed_attempts[identifier]
            return False, 0
        
        # Check if max attempts exceeded
        if count >= self._max_attempts:
            remaining = int(self._lockout_duration - (now - timestamp))
            return True, max(0, remaining)
        
        return False, 0

# Global brute force protection
brute_force_protection = BruteForceProtection()

# ─── IP Whitelist/Blacklist ───
class IPFilter:
    """IP filtering for additional security"""
    
    def __init__(self):
        self._whitelist: set = set()
        self._blacklist: set = set()
    
    def add_to_whitelist(self, ip: str):
        """Add IP to whitelist"""
        self._whitelist.add(ip)
    
    def add_to_blacklist(self, ip: str):
        """Add IP to blacklist"""
        self._blacklist.add(ip)
    
    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        if ip in self._blacklist:
            return False
        if self._whitelist and ip not in self._whitelist:
            return False
        return True

ip_filter = IPFilter()

# ─── Security Headers ───
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "ALLOW-FROM https://www.erckerala.org",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self' https://www.erckerala.org; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; frame-ancestors 'self' https://www.erckerala.org https://erckerala.org;",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        return response

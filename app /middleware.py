import time
import redis
from functools import wraps
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from flask import request, jsonify, current_app, g
import jwt
from werkzeug.exceptions import HTTPException

# Redis configuration (adjust as needed)
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class APIAccessError(Exception):
    """Custom exception for API access control"""
    def __init__(self, message: str, error_code: str, status_code: int = 403):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)

def api_middleware():
    """Main API middleware decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # 1. Extract and validate API key
                api_key = _extract_api_key()
                key_data = _validate_api_key(api_key)
                
                # 2. Check account status and expiration
                _check_account_status(key_data)
                
                # 3. Enforce rate limiting
                _enforce_rate_limit(key_data)
                
                # 4. Track usage
                _track_usage(key_data)
                
                # Store validated data in Flask's g object for downstream use
                g.api_key = api_key
                g.user_id = key_data['user_id']
                g.plan = key_data['plan']
                g.api_name = key_data.get('api_name', 'default')
                
                return f(*args, **kwargs)
                
            except APIAccessError as e:
                return _create_error_response(e.message, e.error_code, e.status_code)
            except HTTPException as e:
                return _create_error_response(str(e), 'HTTP_ERROR', e.code)
            except Exception as e:
                current_app.logger.error(f"Unexpected error in API middleware: {str(e)}")
                return _create_error_response(
                    "An internal error occurred while processing your request",
                    "INTERNAL_ERROR",
                    500
                )
        return decorated_function
    return decorator

def _extract_api_key() -> str:
    """Extract API key from request headers or query parameters"""
    # Check Authorization header (Bearer scheme)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1].strip()
    
    # Check API-Key header
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return api_key.strip()
    
    # Check query parameter (less secure, but sometimes needed)
    api_key = request.args.get('api_key')
    if api_key:
        return api_key.strip()
    
    raise APIAccessError(
        "API key is required. Please provide a valid key in the Authorization header (Bearer scheme), X-API-Key header, or api_key query parameter.",
        "MISSING_API_KEY",
        401
    )

def _validate_api_key(api_key: str) -> Dict[str, Any]:
    """Validate API key and retrieve associated data"""
    # Cache lookup to reduce database hits
    cache_key = f"api_key:{api_key}"
    cached_data = redis_client.hgetall(cache_key)
    
    if cached_data:
        # Convert string values to appropriate types
        return {
            'user_id': cached_data['user_id'],
            'plan': cached_data['plan'],
            'status': cached_data['status'],
            'expires_at': datetime.fromisoformat(cached_data['expires_at']) if cached_data.get('expires_at') else None,
            'api_name': cached_data.get('api_name', 'default'),
            'rate_limit': int(cached_data['rate_limit']),
            'rate_window': int(cached_data['rate_window'])
        }
    
    # If not in cache, validate with your database (example implementation)
    key_data = _query_database_for_key(api_key)
    
    if not key_data:
        raise APIAccessError(
            "Invalid API key. Please verify your key and try again.",
            "INVALID_API_KEY",
            401
        )
    
    # Cache the valid key (with 5-minute expiration to handle key revocation)
    redis_client.hmset(cache_key, {
        'user_id': key_data['user_id'],
        'plan': key_data['plan'],
        'status': key_data['status'],
        'expires_at': key_data['expires_at'].isoformat() if key_data.get('expires_at') else '',
        'api_name': key_data.get('api_name', 'default'),
        'rate_limit': key_data['rate_limit'],
        'rate_window': key_data['rate_window']
    })
    redis_client.expire(cache_key, 300)  # 5 minutes
    
    return key_data

def _query_database_for_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Query your database for API key information (implement based on your DB)"""
    # Example implementation - replace with your actual database query
    # This is a placeholder that would normally query your database
    # In production, use parameterized queries to prevent SQL injection
    
    # Sample response structure:
    # return {
    #     'user_id': 'user_123',
    #     'plan': 'premium',
    #     'status': 'active',
    #     'expires_at': datetime(2026, 1, 1, tzinfo=timezone.utc),
    #     'api_name': 'payment_api',
    #     'rate_limit': 1000,
    #     'rate_window': 3600  # seconds
    # }
    raise NotImplementedError("Implement database query for API key validation")

def _check_account_status(key_data: Dict[str, Any]):
    """Verify account is active and not expired"""
    # Check status
    if key_data['status'] != 'active':
        raise APIAccessError(
            "Your account is currently inactive. Please contact support to reactivate your account.",
            "ACCOUNT_INACTIVE",
            403
        )
    
    # Check expiration
    expires_at = key_data.get('expires_at')
    if expires_at and datetime.now(timezone.utc) > expires_at:
        raise APIAccessError(
            "Your API access has expired. Please renew your subscription to continue using the service.",
            "API_KEY_EXPIRED",
            403
        )

def _enforce_rate_limit(key_data: Dict[str, Any]):
    """Enforce plan-based rate limiting"""
    user_id = key_data['user_id']
    plan = key_data['plan']
    api_name = key_data.get('api_name', 'default')
    
    # Construct Redis keys for rate limiting
    user_limit_key = f"rate_limit:user:{user_id}"
    api_limit_key = f"rate_limit:api:{api_name}:{user_id}"
    
    # Get current timestamp
    now = int(time.time())
    window = key_data['rate_window']
    limit = key_data['rate_limit']
    
    # Clean old entries and count current requests (using Redis pipeline for efficiency)
    pipeline = redis_client.pipeline()
    
    # User-wide rate limit
    pipeline.zremrangebyscore(user_limit_key, 0, now - window)
    pipeline.zcard(user_limit_key)
    pipeline.zadd(user_limit_key, {str(now): now})
    pipeline.expire(user_limit_key, window)
    
    # API-specific rate limit
    pipeline.zremrangebyscore(api_limit_key, 0, now - window)
    pipeline.zcard(api_limit_key)
    pipeline.zadd(api_limit_key, {str(now): now})
    pipeline.expire(api_limit_key, window)
    
    results = pipeline.execute()
    
    user_count = results[1]
    api_count = results[5]
    
    # Check if limits are exceeded
    if user_count > limit:
        reset_time = now + window - (now % window)
        raise APIAccessError(
            f"Rate limit exceeded for your plan. Maximum {limit} requests per {window} seconds.",
            "RATE_LIMIT_EXCEEDED",
            429,
            headers={'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Reset': str(reset_time)}
        )
    
    if api_count > limit:
        reset_time = now + window - (now % window)
        raise APIAccessError(
            f"Rate limit exceeded for this API endpoint. Maximum {limit} requests per {window} seconds.",
            "API_RATE_LIMIT_EXCEEDED",
            429,
            headers={'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Reset': str(reset_time)}
        )

def _track_usage(key_data: Dict[str, Any]):
    """Track API usage for billing and analytics"""
    user_id = key_data['user_id']
    api_name = key_data.get('api_name', 'default')
    plan = key_data['plan']
    
    # Current timestamp for daily/hourly tracking
    now = datetime.now(timezone.utc)
    day_key = now.strftime("%Y-%m-%d")
    hour_key = now.strftime("%Y-%m-%d:%H")
    
    # Track user usage
    redis_client.incr(f"usage:user:{user_id}:total")
    redis_client.incr(f"usage:user:{user_id}:daily:{day_key}")
    redis_client.incr(f"usage:user:{user_id}:hourly:{hour_key}")
    
    # Track API usage
    redis_client.incr(f"usage:api:{api_name}:total")
    redis_client.incr(f"usage:api:{api_name}:daily:{day_key}")
    redis_client.incr(f"usage:api:{api_name}:hourly:{hour_key}")
    
    # Track plan usage
    redis_client.incr(f"usage:plan:{plan}:total")
    redis_client.incr(f"usage:plan:{plan}:daily:{day_key}")
    
    # Optional: Log to persistent storage for billing (async to avoid blocking)
    # In production, use a task queue like Celery for this
    # _log_to_persistent_storage(user_id, api_name, plan, request.endpoint)

def _create_error_response(message: str, error_code: str, status_code: int, headers: Dict = None):
    """Create standardized error response"""
    response = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": getattr(g, 'request_id', 'unknown')
        },
        "support": {
            "documentation": "https://api.yourservice.com/docs/errors",
            "contact": "support@yourservice.com"
        }
    }
    
    # Add helpful hints for common errors
    if error_code == "RATE_LIMIT_EXCEEDED":
        response["error"]["hint"] = "Consider upgrading your plan or implementing request queuing in your application."
    elif error_code == "API_KEY_EXPIRED":
        response["error"]["hint"] = "Renew your subscription at https://app.yourservice.com/billing"
    elif error_code == "ACCOUNT_INACTIVE":
        response["error"]["hint"] = "Contact support@yourservice.com to reactivate your account."
    
    resp = jsonify(response)
    resp.status_code = status_code
    
    if headers:
        for key, value in headers.items():
            resp.headers[key] = str(value)
    
    return resp

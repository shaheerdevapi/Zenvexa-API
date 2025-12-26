"""
Zenvexa API - Middleware Module
Production-ready API key validation and rate limiting middleware
Replaces the existing middleware with enhanced features
"""

import os
import time
from functools import wraps
from flask import request, jsonify, g
from extensions import db
from models import APIKey, APIUsage, API, User, Subscription
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enhanced rate limiting configuration
RATE_LIMITS = {
    'free': {'minute': 10, 'hour': 100, 'day': 1000, 'month': 10000},
    'starter': {'minute': 30, 'hour': 300, 'day': 3000, 'month': 30000},
    'pro': {'minute': 100, 'hour': 1000, 'day': 10000, 'month': 100000},
    'enterprise': {'minute': 500, 'hour': 5000, 'day': 50000, 'month': 500000}
}

# Enhanced error response templates
ERROR_RESPONSES = {
    'missing_key': {
        'error': 'authentication_required',
        'message': 'API key is required. Include X-API-Key header in your request.',
        'documentation': 'https://zenvexa.com/docs/authentication'
    },
    'invalid_key': {
        'error': 'invalid_api_key',
        'message': 'The provided API key is invalid or malformed.',
        'documentation': 'https://zenvexa.com/docs/authentication'
    },
    'suspended_key': {
        'error': 'api_key_suspended',
        'message': 'Your API key has been suspended due to policy violations.',
        'support': 'sherry.aitools1@gmail.com'
    },
    'expired_key': {
        'error': 'api_key_expired',
        'message': 'Your API key has expired. Please renew your subscription.',
        'upgrade_url': 'https://zenvexa.com/pricing'
    },
    'rate_limit_exceeded': {
        'error': 'rate_limit_exceeded',
        'message': 'You have exceeded your rate limit.',
        'limit': None,
        'period': None,
        'resets_at': None,
        'upgrade_url': 'https://zenvexa.com/pricing'
    },
    'no_subscription': {
        'error': 'no_active_subscription',
        'message': 'No active subscription found. Please subscribe to use the API.',
        'subscribe_url': 'https://zenvexa.com/pricing'
    },
    'api_not_found': {
        'error': 'api_not_found',
        'message': 'The requested API endpoint was not found.',
        'documentation': 'https://zenvexa.com/docs/api'
    },
    'api_inactive': {
        'error': 'api_not_available',
        'message': 'This API is currently unavailable.',
        'status': None
    },
    'access_denied': {
        'error': 'access_denied',
        'message': 'You do not have permission to access this API.',
        'documentation': 'https://zenvexa.com/docs/access-control'
    },
    'admin_required': {
        'error': 'admin_access_required',
        'message': 'Admin privileges are required for this action.',
        'documentation': 'https://zenvexa.com/docs/admin'
    }
}


def validate_api_key(f):
    """
    Enhanced API key validation with detailed error responses
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract API key
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify(ERROR_RESPONSES['missing_key']), 401
        
        # Validate API key
        key_record = APIKey.query.filter_by(key=api_key).first()
        
        if not key_record:
            return jsonify(ERROR_RESPONSES['invalid_key']), 401
        
        # Check key status
        if key_record.status == 'suspended':
            return jsonify(ERROR_RESPONSES['suspended_key']), 403
        
        if key_record.status == 'inactive':
            return jsonify(ERROR_RESPONSES['invalid_key']), 401
        
        # Check expiration
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            key_record.status = 'expired'
            db.session.commit()
            return jsonify(ERROR_RESPONSES['expired_key']), 403
        
        # Store in g for downstream use
        g.api_key = key_record
        g.user = key_record.user
        
        return f(*args, **kwargs)
    
    return decorated_function


def check_rate_limit(f):
    """
    Enhanced rate limiting with multiple time windows
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'api_key') or not hasattr(g, 'user'):
            return jsonify({'error': 'Authentication required'}), 401
        
        user = g.user
        subscription = Subscription.query.filter_by(
            user_id=user.id,
            status='active'
        ).first()
        
        if not subscription:
            return jsonify(ERROR_RESPONSES['no_subscription']), 403
        
        plan = subscription.plan
        now = datetime.utcnow()
        
        # Determine rate limit period and window
        rate_limit_period = plan.rate_limit_period or 'hour'
        rate_limit = plan.rate_limit or 100
        
        # Calculate time window
        time_windows = {
            'minute': timedelta(minutes=1),
            'hour': timedelta(hours=1),
            'day': timedelta(days=1),
            'month': timedelta(days=30)
        }
        
        time_window = time_windows.get(rate_limit_period, timedelta(hours=1))
        window_start = now - time_window
        
        # Count usage in current window
        usage_count = APIUsage.query.filter(
            APIUsage.api_key_id == g.api_key.id,
            APIUsage.timestamp >= window_start
        ).count()
        
        # Check if limit exceeded
        if usage_count >= rate_limit:
            error_response = ERROR_RESPONSES['rate_limit_exceeded'].copy()
            error_response.update({
                'limit': rate_limit,
                'period': rate_limit_period,
                'resets_at': (window_start + time_window).isoformat(),
                'current_usage': usage_count
            })
            return jsonify(error_response), 429
        
        # Store subscription info for downstream use
        g.subscription = subscription
        g.plan = plan
        
        return f(*args, **kwargs)
    
    return decorated_function


def track_usage(api_id=None):
    """
    Enhanced usage tracking with detailed metrics
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'api_key'):
                return jsonify({'error': 'Authentication required'}), 401
            
            start_time = time.time()
            
            # Execute the actual function
            response = f(*args, **kwargs)
            
            # Calculate response time
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)
            
            # Determine API ID
            target_api_id = api_id or kwargs.get('api_id') or request.view_args.get('api_id')
            
            # Extract status code from response
            if isinstance(response, tuple):
                status_code = response[1]
                response_data = response[0]
            else:
                status_code = 200
                response_data = response
            
            # Log usage if API ID is available
            if target_api_id:
                try:
                    usage = APIUsage(
                        api_key_id=g.api_key.id,
                        api_id=target_api_id,
                        endpoint=request.path,
                        method=request.method,
                        status_code=status_code,
                        response_time=response_time,
                        ip_address=request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown'),
                        timestamp=datetime.utcnow()
                    )
                    
                    db.session.add(usage)
                    db.session.commit()
                    
                    logger.info(f"API usage tracked: {g.api_key.id} -> {target_api_id} ({status_code})")
                    
                except Exception as e:
                    logger.error(f"Failed to track usage: {e}")
                    db.session.rollback()
            
            return response
        
        return decorated_function
    return decorator


def require_api_access(f):
    """
    Enhanced API access control with proper error handling
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_id = kwargs.get('api_id') or request.view_args.get('api_id')
        
        if not api_id:
            return jsonify({'error': 'API ID is required'}), 400
        
        # Fetch API
        api = API.query.get(api_id)
        
        if not api:
            return jsonify(ERROR_RESPONSES['api_not_found']), 404
        
        # Check API status
        if api.status != 'active':
            error_response = ERROR_RESPONSES['api_inactive'].copy()
            error_response['status'] = api.status
            return jsonify(error_response), 403
        
        # Check user authentication
        if not hasattr(g, 'user'):
            return jsonify({'error': 'Authentication required'}), 401
        
        # Check access permissions
        if api.access_type == 'private' and api.owner_id != g.user.id:
            return jsonify(ERROR_RESPONSES['access_denied']), 403
        
        # Store API in g for downstream use
        g.api = api
        
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f):
    """
    Enhanced admin access control
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user'):
            return jsonify({'error': 'Authentication required'}), 401
        
        if g.user.role != 'admin':
            return jsonify(ERROR_RESPONSES['admin_required']), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


# Combined decorators for common use cases
def api_auth_required(f):
    """
    Combined authentication decorator that validates API key and checks rate limits
    """
    return validate_api_key(check_rate_limit(f))


def full_api_access(api_id=None):
    """
    Combined decorator that provides full API access control
    """
    def decorator(f):
        return validate_api_key(
            check_rate_limit(
                require_api_access(
                    track_usage(api_id)(f)
                )
            )
        )
    return decorator


# Utility functions
def get_client_ip():
    """Get client IP address from request"""
    return request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or \
           request.headers.get('X-Real-IP') or \
           request.remote_addr or \
           'unknown'


def log_security_event(event_type, details=None):
    """Log security events for monitoring"""
    logger.warning(f"Security Event: {event_type} - User: {getattr(g, 'user', None)} - IP: {get_client_ip()}")
    if details:
        logger.warning(f"Details: {details}")


# Example usage
if __name__ == "__main__":
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/api/test/<int:api_id>')
    @full_api_access(api_id=None)
    def test_endpoint(api_id):
        return jsonify({
            'message': 'Success',
            'api_id': api_id,
            'user': g.user.email,
            'plan': g.plan.name
        })
    
    app.run(debug=True)

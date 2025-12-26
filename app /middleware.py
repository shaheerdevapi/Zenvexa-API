import os
import time
from functools import wraps
from flask import request, jsonify, g
from extensions import db
from models import APIKey, APIUsage, API, User, Subscription
from datetime import datetime, timedelta

def validate_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        key_record = APIKey.query.filter_by(key=api_key).first()
        
        if not key_record:
            return jsonify({'error': 'Invalid API key'}), 401
        
        if key_record.status != 'active':
            return jsonify({'error': f'API key is {key_record.status}'}), 403
        
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            key_record.status = 'expired'
            db.session.commit()
            return jsonify({'error': 'API key has expired'}), 403
        
        g.api_key = key_record
        g.user = key_record.user
        
        return f(*args, **kwargs)
    
    return decorated_function

def check_rate_limit(f):
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
            return jsonify({'error': 'No active subscription'}), 403
        
        plan = subscription.plan
        now = datetime.utcnow()
        
        if plan.rate_limit_period == 'minute':
            time_window = now - timedelta(minutes=1)
        elif plan.rate_limit_period == 'hour':
            time_window = now - timedelta(hours=1)
        elif plan.rate_limit_period == 'day':
            time_window = now - timedelta(days=1)
        else:
            time_window = now - timedelta(days=30)
        
        usage_count = APIUsage.query.filter(
            APIUsage.api_key_id == g.api_key.id,
            APIUsage.timestamp >= time_window
        ).count()
        
        if usage_count >= plan.rate_limit:
            return jsonify({
                'error': 'Rate limit exceeded',
                'limit': plan.rate_limit,
                'period': plan.rate_limit_period,
                'reset_at': (time_window + timedelta(
                    minutes=1 if plan.rate_limit_period == 'minute' else 0,
                    hours=1 if plan.rate_limit_period == 'hour' else 0,
                    days=1 if plan.rate_limit_period == 'day' else 30
                )).isoformat()
            }), 429
        
        g.subscription = subscription
        g.plan = plan
        
        return f(*args, **kwargs)
    
    return decorated_function

def track_usage(api_id=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'api_key'):
                return jsonify({'error': 'Authentication required'}), 401
            
            start_time = time.time()
            
            response = f(*args, **kwargs)
            
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)
            
            target_api_id = api_id or kwargs.get('api_id') or request.view_args.get('api_id')
            
            if target_api_id:
                usage = APIUsage(
                    api_key_id=g.api_key.id,
                    api_id=target_api_id,
                    endpoint=request.path,
                    method=request.method,
                    status_code=response[1] if isinstance(response, tuple) else 200,
                    response_time=response_time,
                    ip_address=request.remote_addr,
                    timestamp=datetime.utcnow()
                )
                
                db.session.add(usage)
                db.session.commit()
            
            return response
        
        return decorated_function
    return decorator

def require_api_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_id = kwargs.get('api_id') or request.view_args.get('api_id')
        
        if not api_id:
            return jsonify({'error': 'API ID required'}), 400
        
        api = API.query.get(api_id)
        
        if not api:
            return jsonify({'error': 'API not found'}), 404
        
        if api.status != 'active':
            return jsonify({'error': f'API is {api.status}'}), 403
        
        if not hasattr(g, 'user'):
            return jsonify({'error': 'Authentication required'}), 401
        
        if api.access_type == 'private' and api.owner_id != g.user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        g.api = api
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user'):
            return jsonify({'error': 'Authentication required'}), 401
        
        if g.user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

from functools import wraps
from flask import request, current_app
from utils.responses import validation_error
import time

def validate_json(*fields):
    """Decorator to validate required fields in JSON request body"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return validation_error("Request body must be JSON")
            
            data = request.get_json()
            missing = [field for field in fields if field not in data]
            
            if missing:
                return validation_error(f"Missing required fields: {', '.join(missing)}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_request(f):
    """Decorator to log request details and execution time"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        current_app.logger.info(f"Starting {request.method} {request.path}")
        
        response = f(*args, **kwargs)
        
        duration = time.time() - start_time
        current_app.logger.info(f"Finished {request.method} {request.path} in {duration:.4f}s")
        
        return response
    return decorated_function

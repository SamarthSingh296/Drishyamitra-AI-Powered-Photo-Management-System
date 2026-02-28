from functools import wraps
from flask import request, current_app, jsonify
from utils.responses import validation_error, error_response
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask_jwt_extended.exceptions import NoAuthorizationError
import time
import traceback

def validate_json(*fields):
    """Decorator to validate required fields in JSON request body"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return validation_error("Request body must be JSON")
            
            try:
                data = request.get_json()
            except Exception:
                return validation_error("Invalid JSON format")
                
            missing = [field for field in fields if field not in data]
            
            if missing:
                return validation_error(f"Missing required fields: {', '.join(missing)}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def secure_route(admin_only=False):
    """Unified decorator for authentication and role check"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                if admin_only and claims.get("role") != "admin":
                    return error_response("Admin privileges required", 403)
                return f(*args, **kwargs)
            except NoAuthorizationError:
                return error_response("Missing or invalid authorization token", 401)
            except Exception as e:
                return error_response(f"Authentication failed: {str(e)}", 401)
        return decorated_function
    return decorator

def log_request(f):
    """Decorator to log request details, execution time and errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        path = request.path
        method = request.method
        current_app.logger.info(f">>> Starting {method} {path}")
        
        try:
            response = f(*args, **kwargs)
            duration = time.time() - start_time
            
            # Extract status code from response if it's a tuple or Response object
            status_code = 200
            if isinstance(response, tuple):
                status_code = response[1]
            elif hasattr(response, 'status_code'):
                status_code = response.status_code
            
            current_app.logger.info(f"<<< Finished {method} {path} | Status: {status_code} | Duration: {duration:.4f}s")
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"!!! Error in {method} {path}: {str(e)}\n{traceback.format_exc()}"
            current_app.logger.error(error_msg)
            return error_response("An internal server error occurred", 500)
            
    return decorated_function

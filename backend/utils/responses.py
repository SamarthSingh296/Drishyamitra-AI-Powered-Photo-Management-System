from flask import jsonify

def success_response(data=None, message="Success", status_code=200):
    """Standard success response"""
    return jsonify({
        "status": "success",
        "message": message,
        "data": data
    }), status_code

def error_response(message="An error occurred", status_code=500, errors=None):
    """Standard error response"""
    response = {
        "status": "error",
        "message": message
    }
    if errors:
        response["errors"] = errors
    return jsonify(response), status_code

def validation_error(errors):
    """Standard validation error response"""
    return error_response(message="Validation failed", status_code=400, errors=errors)

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token, 
    jwt_required, 
    get_jwt_identity
)
from models.database import db
from models.user import User
from utils.responses import success_response, error_response
from utils.validation import validate_json_fields

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
@validate_json_fields('username', 'email', 'password')
def register():
    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return error_response("Username already exists", 400)
    
    if User.query.filter_by(email=data['email']).first():
        return error_response("Email already exists", 400)
    
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return success_response(user.to_dict(), "User registered successfully", 201)

@auth_bp.route('/login', methods=['POST'])
@validate_json_fields('username', 'password')
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
        refresh_token = create_refresh_token(identity=str(user.id), additional_claims={"role": user.role})
        
        return success_response({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict()
        }, "Login successful")
    
    return error_response("Invalid credentials", 401)

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Endpoint to refresh access tokens"""
    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id)
    return success_response({"access_token": new_access_token}, "Token refreshed")

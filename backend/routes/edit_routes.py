from flask import Blueprint, jsonify

edit_bp = Blueprint('edit', __name__)

@edit_bp.route('/', methods=['POST'])
def edit():
    return jsonify({"message": "Edit endpoint stub"}), 200

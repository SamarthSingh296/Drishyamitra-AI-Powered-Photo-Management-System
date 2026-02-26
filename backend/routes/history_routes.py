from flask import Blueprint, jsonify

history_bp = Blueprint('history', __name__)

@history_bp.route('/', methods=['GET'])
def history():
    return jsonify({"message": "History endpoint stub"}), 200

from flask import Blueprint, jsonify

delivery_bp = Blueprint('delivery', __name__)

@delivery_bp.route('/', methods=['GET'])
def delivery():
    return jsonify({"message": "Delivery endpoint stub"}), 200

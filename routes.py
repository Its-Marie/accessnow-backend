from flask import Blueprint, request, jsonify, abort
from app import db
from models import User
from schemas import user_schema, users_schema
import json

api_bp = Blueprint("api", __name__)

# GET /api/users
@api_bp.get("/users")
def list_users():
    users = User.query.order_by(User.id.desc()).all()
    return users_schema.jsonify(users), 200

# GET /api/users/<id>
@api_bp.get("/users/<int:user_id>")
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return user_schema.jsonify(user), 200

# POST /api/users
@api_bp.post("/users")
def create_user():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email")
    name = data.get("name")
    password = data.get("password")
    needs = data.get("needs")  # dict or list preferred

    if not all([email, name, password]):
        abort(400, description="email, name, password are required")

    if User.query.filter_by(email=email).first():
        abort(409, description="email already exists")

    user = User(email=email, name=name, needs=json.dumps(needs) if needs else None)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user_schema.jsonify(user), 201

# PUT /api/users/<id>
@api_bp.put("/users/<int:user_id>")
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(force=True, silent=True) or {}

    if "email" in data:
        # prevent duplicate emails
        conflict = User.query.filter(User.email == data["email"], User.id != user_id).first()
        if conflict:
            abort(409, description="email already in use")
        user.email = data["email"]

    if "name" in data:
        user.name = data["name"]

    if "password" in data and data["password"]:
        user.set_password(data["password"])

    if "needs" in data:
        user.needs = json.dumps(data["needs"]) if data["needs"] is not None else None

    db.session.commit()
    return user_schema.jsonify(user), 200

# DELETE /api/users/<id>
@api_bp.delete("/users/<int:user_id>")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify(message="deleted"), 200

from flask import Blueprint, request, jsonify, abort, current_app
from extensions import db   
from models import User
from schemas import user_schema, users_schema
from pyproj import Transformer
import json
import os

TRANSFORMER_25833_TO_4326 = Transformer.from_crs(
    "EPSG:25833", "EPSG:4326", always_xy=True
)

api_bp = Blueprint("api", __name__)
data_bp = Blueprint("data", __name__)

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


@api_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        abort(400, description="email and password are required")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        abort(401, description="invalid credentials")

    needs = None
    if user.needs:
        try:
            needs = json.loads(user.needs)
        except json.JSONDecodeError:
            needs = user.needs

    user_payload = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "needs": needs,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

    return jsonify(message="login successful", user=user_payload), 200

@data_bp.get("/toilets")
def get_toilets():
    base = current_app.root_path
    path = os.path.join(base, "Datapoints", "toilets.json")
    if not os.path.exists(path):
        abort(404, description="toilets dataset missing")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data.get("features", []):
        geom = feature.get("geometry")
        if not geom or geom.get("type") != "Point":
            continue
        x,y = geom["coordinates"] 
        lon, lat = TRANSFORMER_25833_TO_4326.transform(x, y)
        geom["coordinates"] = [lon, lat]

    return jsonify(data), 200

@data_bp.get("/accessible_parking")
def get_accessible_parking():
    base = current_app.root_path
    path = os.path.join(base, "Datapoints", "accessible_parking.json")
    if not os.path.exists(path):
        abort(404, description="parking dataset missing")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data.get("features", []):
        geom = feature.get("geometry")
        if not geom or geom.get("type") != "Point":
            continue
        x,y = geom["coordinates"] 
        lon, lat = TRANSFORMER_25833_TO_4326.transform(x, y)
        geom["coordinates"] = [lon, lat]

    return jsonify(data), 200


@data_bp.get("/elevators")
def get_elevators():
    base = current_app.root_path
    path = os.path.join(base, "Datapoints", "elevators.json")
    if not os.path.exists(path):
        abort(404, description="elevators dataset missing")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data.get("features", []):
        geom = feature.get("geometry")
        if not geom or geom.get("type") != "Point":
            continue
        x,y = geom["coordinates"] 
        lon, lat = TRANSFORMER_25833_TO_4326.transform(x, y)
        geom["coordinates"] = [lon, lat]

    return jsonify(data), 200
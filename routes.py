from flask import Blueprint, request, jsonify, abort, current_app
from extensions import db   
from models import User
from schemas import user_schema, users_schema
from pyproj import Transformer
import json
import os
import requests


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

@api_bp.post("/plan-route")
def plan_route():
    """
    MVP: One endpoint for everything
    Input: { start: "address", destination: "address", show_toilets, show_elevators, show_parking }
    Output: { route, pois, start, destination }
    """
    data = request.get_json(force=True, silent=True) or {}
    start_text = data.get("start")
    dest_text = data.get("destination")
    show_toilets = data.get("show_toilets", True)
    show_elevators = data.get("show_elevators", True)
    show_parking = data.get("show_parking", True)
    
    if not start_text or not dest_text:
        abort(400, description="start and destination required")
    
    # Step 1: Geocode start address
    start_coords = geocode_address(start_text)
    if not start_coords:
        return jsonify(error="Start address not found"), 404
    
    # Step 2: Geocode destination address
    dest_coords = geocode_address(dest_text)
    if not dest_coords:
        return jsonify(error="Destination address not found"), 404
    
    # Step 3: Calculate route (foot only for MVP)
    route = calculate_osrm_route(start_coords, dest_coords, profile='foot')
    if not route:
        return jsonify(error="Could not calculate route"), 500
    
    # Step 4: Load filtered POIs
    pois = load_filtered_pois(show_toilets, show_elevators, show_parking)
    
    return jsonify({
        "route": route,
        "pois": pois,
        "start": {"coords": start_coords, "address": start_text},
        "destination": {"coords": dest_coords, "address": dest_text}
    }), 200


def geocode_address(address):
    """Convert address string to [lon, lat] coordinates"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "countrycodes": "de"
    }
    headers = {"User-Agent": "AccessNow+ App"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()
        
        if results:
            return [float(results[0]['lon']), float(results[0]['lat'])]
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None


def calculate_osrm_route(start, destination, profile='foot'):
    """Calculate route using OSRM and return GeoJSON Feature"""
    url = f"http://router.project-osrm.org/route/v1/{profile}/{start[0]},{start[1]};{destination[0]},{destination[1]}"
    params = {
        "overview": "full",
        "geometries": "geojson"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('routes'):
            route = data['routes'][0]
            return {
                "type": "Feature",
                "geometry": route['geometry'],
                "properties": {
                    "distance": route['distance'],  # meters
                    "duration": route['duration']   # seconds
                }
            }
        return None
    except Exception as e:
        print(f"Routing error: {e}")
        return None

def load_filtered_pois(show_toilets, show_elevators, show_parking):
    base = current_app.root_path
    all_pois = {"type": "FeatureCollection", "features": []}
    
    # Toilets
    if show_toilets:
        toilets_path = os.path.join(base, "Datapoints", "toilets.json")
        if os.path.exists(toilets_path):
            with open(toilets_path, "r", encoding="utf-8") as f:
                toilets_data = json.load(f)
                for feature in toilets_data.get("features", []):
                    geom = feature.get("geometry")
                    if geom and geom.get("type") == "Point":
                        x, y = geom["coordinates"]
                        lon, lat = TRANSFORMER_25833_TO_4326.transform(x, y)
                        feature["geometry"]["coordinates"] = [lon, lat]
                        feature["properties"]["poi_type"] = "toilet"
                        all_pois["features"].append(feature)
    
    # Elevators
    if show_elevators:
        elevators_path = os.path.join(base, "Datapoints", "elevators.json")
        if os.path.exists(elevators_path):
            with open(elevators_path, "r", encoding="utf-8") as f:
                elevators_data = json.load(f)
                for feature in elevators_data.get("features", []):
                    geom = feature.get("geometry")
                    if geom and geom.get("type") == "Point":
                        x, y = geom["coordinates"]
                        lon, lat = TRANSFORMER_25833_TO_4326.transform(x, y)
                        feature["geometry"]["coordinates"] = [lon, lat]
                        feature["properties"]["poi_type"] = "elevator"
                        all_pois["features"].append(feature)
    
    # Accessible parking
    if show_parking:
        parking_path = os.path.join(base, "Datapoints", "accessible_parking.json")
        if os.path.exists(parking_path):
            with open(parking_path, "r", encoding="utf-8") as f:
                parking_data = json.load(f)
                for feature in parking_data.get("features", []):
                    geom = feature.get("geometry")
                    if geom and geom.get("type") == "Point":
                        x, y = geom["coordinates"]
                        lon, lat = TRANSFORMER_25833_TO_4326.transform(x, y)
                        feature["geometry"]["coordinates"] = [lon, lat]
                        feature["properties"]["poi_type"] = "parking"
                        all_pois["features"].append(feature)
    
    return all_pois

@api_bp.post("/route")
def calculate_route():
    """Legacy route endpoint - coordinates input"""
    data = request.get_json(force=True, silent=True) or {}
    start = data.get("start")  # [lon, lat]
    destination = data.get("destination")  # [lon, lat]
    
    if not start or not destination:
        abort(400, description="start and destination required")
    
    osrm_url = f"http://router.project-osrm.org/route/v1/foot/{start[0]},{start[1]};{destination[0]},{destination[1]}"
    
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }
    
    try:
        response = requests.get(osrm_url, params=params, timeout=30)
        response.raise_for_status()
        route_data = response.json()
        return jsonify(route_data), 200
    except Exception as e:
        return jsonify(error=str(e)), 500


@api_bp.get("/geocode")
def geocode():
    """Legacy geocode endpoint - query parameter"""
    query = request.args.get("q")
    
    if not query:
        abort(400, description="query required")
    
    nominatim_url = "https://nominatim.openstreetmap.org/search"
    
    params = {
        "q": query,
        "format": "json",
        "limit": 5,
        "countrycodes": "de",
        "addressdetails": 1
    }
    
    headers = {
        "User-Agent": "AccessNow+ App"
    }
    
    try:
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()
        return jsonify(results), 200
    except Exception as e:
        return jsonify(error=str(e)), 500
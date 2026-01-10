from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from config import Config
from flask_cors import CORS
from routes import api_bp, data_bp

app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(data_bp, url_prefix="/api")


db = SQLAlchemy()
ma = Marshmallow()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    app.config.from_object(Config)
    db.init_app(app)
    ma.init_app(app)


    # Import models so migrations see them
    from models import User
    
    migrate.init_app(app, db)

    # Register routes
    from routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    return app

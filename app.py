import os
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from extensions import db, ma, migrate, jwt

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, origins=[
    os.getenv("FRONTEND_URL", "http://localhost:5173")
])

    # init extensions
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # register blueprints
    from routes import api_bp, data_bp
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(data_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    return app

# Flask CLI entrypoint
app = create_app()

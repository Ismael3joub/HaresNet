from flask import Flask, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from config import config
import os

# Initialize extensions (singletons)
db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*", logger=True, engineio_logger=True)


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # Allow cross-origin requests for API endpoints and expose Authorization header
    app.config['CORS_HEADERS'] = 'Content-Type,Authorization'
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize Socket.IO with Flask app
    socketio.init_app(app)

    # Register blueprints
    from app.api import auth, devices, wifi, firewall, schedules, system, settings
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(devices.bp, url_prefix='/api/devices')
    app.register_blueprint(wifi.bp, url_prefix='/api/wifi')
    app.register_blueprint(firewall.bp, url_prefix='/api/firewall')
    app.register_blueprint(schedules.bp, url_prefix='/api/schedules')
    app.register_blueprint(system.bp, url_prefix='/api/system')
    app.register_blueprint(settings.bp, url_prefix='/api/settings')
    
    from app.api import network, router, dns_filter
    app.register_blueprint(network.bp, url_prefix='/api/network')
    app.register_blueprint(router.bp, url_prefix='/api/router')
    app.register_blueprint(dns_filter.bp, url_prefix='/api/dns_filter')

    # Create database tables and default admin
    with app.app_context():
        db.create_all()

        # Enable WAL mode for SQLite to support concurrent reads/writes
        # from background jobs (traffic monitor, device discovery, scheduler)
        if not app.config.get('TESTING'):
            from sqlalchemy import text
            db.session.execute(text("PRAGMA journal_mode=WAL"))
            db.session.execute(text("PRAGMA synchronous=NORMAL"))
            db.session.execute(text("PRAGMA busy_timeout=30000"))
            db.session.commit()
            
            # Register REGEXP function for SQLite
            from sqlalchemy import event
            from sqlalchemy.engine import Engine
            import re

            @event.listens_for(Engine, "connect")
            def sqlite_engine_connect(dbapi_connection, connection_record):
                # Check if it's sqlite
                if hasattr(dbapi_connection, 'create_function'):
                    def regexp(expr, item):
                        if item is None:
                            return False
                        try:
                            reg = re.compile(expr, re.IGNORECASE)
                            return reg.search(item) is not None
                        except Exception:
                            return False
                    dbapi_connection.create_function("REGEXP", 2, regexp)

        from app.models import User
        if not User.query.filter_by(username=app.config['DEFAULT_ADMIN_USER']).first():
            admin = User(username=app.config['DEFAULT_ADMIN_USER'])
            admin.set_password(app.config['DEFAULT_ADMIN_PASSWORD'])
            db.session.add(admin)
            db.session.commit()

    # Serve frontend static files (MUST be last to not override API routes)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve the React frontend"""
        static_folder = os.path.join(app.root_path, 'static', 'dist')
        
        # If path is a file that exists, serve it
        if path and os.path.exists(os.path.join(static_folder, path)):
            return send_from_directory(static_folder, path)
        
        # Otherwise, serve index.html (for SPA routing)
        index_path = os.path.join(static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_file(index_path)
        
        # If frontend not built, return helpful message
        return {
            'message': 'Frontend not built. Please run: cd ../guardian-angel && npm run build',
            'status': 'frontend_missing'
        }, 404

    return app


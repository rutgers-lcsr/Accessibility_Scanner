from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import inspect
from models import db
from authentication.login import jwt
from models.user import Profile, User
from models.api_key import ApiKey
from mail import mail
from utils.limiter import limiter
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash
import os

def init_admin(app):
    admin_user = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_user or not admin_password:
        print("ADMIN_EMAIL/ADMIN_PASSWORD not set, skipping bootstrap admin user")
        return

    with app.app_context():
        user = db.session.query(User).filter_by(email=admin_user).first()
        if not user:
            try:
                user = User(username=admin_user, email=admin_user)
                user.password = generate_password_hash(admin_password)
                user.profile = Profile(user=user, is_admin=True)
                db.session.add(user)
                db.session.commit()
                print(f"Admin user created with email: {admin_user}")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating admin user: {e}")

def check_api_config(app):
    """Fail fast for settings only the API process needs.

    Called from the API entrypoints (init.sh and __main__) rather than create_app(),
    because the Celery worker also builds the app and does not need these.
    """
    if app.config["TESTING"]:
        return
    if not app.config.get("INTERNAL_AUTH_SECRET"):
        raise RuntimeError(
            "INTERNAL_AUTH_SECRET is not set. It must match the value given to the Next.js "
            "frontend; without it CAS logins are refused (see .env.example)."
        )

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    # Behind nginx -> Next.js; trust one hop of X-Forwarded-For so rate limits see the
    # real client. X-Forwarded-Proto is deliberately NOT trusted: the proxy reaches
    # this app over plain HTTP, and honouring the browser's https would make Flask's
    # trailing-slash redirects point at https://a11y-api:5000, which the proxy cannot
    # follow (every frontend call then failed with a bare 500).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=0)  # x_proto defaults to 1
    # Only the Next.js client origin may make cross-origin requests. Credentials are not
    # allowed because tokens travel in the Authorization header, never in cookies.
    CORS(app, origins=[app.config["CLIENT_URL"]])

    # Swagger docs for the public API key surface (/api/v1).
    # Everything is served under /api/ so the Next.js proxy forwards it.
    from flasgger import Swagger
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "A11y API",
            "description": "Programmatic access to accessibility reports. "
                           "Authenticate with an API key (create one in the app under API Keys).",
            "version": "1.0",
        },
        "securityDefinitions": {
            "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
        },
        "security": [{"ApiKeyAuth": []}],
    }
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec_1",
                "route": "/api/apispec_1.json",
                "rule_filter": lambda rule: rule.rule.startswith("/api/v1"),
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/api/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs/",
    }
    Swagger(app, template=swagger_template, config=swagger_config)

    mail.init_app(app)
    db.init_app(app)
    Migrate(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    
    
    
    app.static_folder = 'static'

    from blueprints.auth import auth_bp
    from blueprints.domains import domain_bp
    from blueprints.report import report_bp
    from blueprints.sites import sites_bp
    from blueprints.user import user_bp
    from blueprints.website import website_bp
    from blueprints.scan import scan_bp
    from blueprints.axe_rules import axe_bp
    from blueprints.settings import settings_bp
    from blueprints.api import api_bp
    from blueprints.api_keys import api_keys_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.findings import findings_bp
    from blueprints.guides import guides_bp
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return {"status": "healthy"}, 200

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(domain_bp, url_prefix='/api/domains')
    app.register_blueprint(report_bp, url_prefix='/api/reports')
    app.register_blueprint(sites_bp, url_prefix='/api/sites')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(website_bp, url_prefix='/api/websites')
    app.register_blueprint(scan_bp, url_prefix='/api/scans')
    app.register_blueprint(axe_bp, url_prefix='/api/axe')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(api_keys_bp, url_prefix='/api/users/me/api-keys')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(findings_bp, url_prefix='/api/findings')
    app.register_blueprint(guides_bp, url_prefix='/api/guides')

    from commands import findings_cli, mail_cli, maintenance_cli
    app.cli.add_command(findings_cli)
    app.cli.add_command(maintenance_cli)
    app.cli.add_command(mail_cli)

    with app.app_context():
        inspector = inspect(db.engine)
        # force schema default to db.engine.url.database
        db.metadata.create_all(bind=db.engine, checkfirst=True)
        if 'settings' in inspector.get_table_names():
            from models.settings import Settings
            Settings.init_defaults()
        

    # set up datetime format for j2 templates
    @app.template_filter('datetimeformat')
    def datetimeformat(value: str, format='%b %d, %Y %I:%M %p'):
        """Format an ISO date string into a more human-readable format, e.g., 'Jun 10, 2024 03:45 PM'."""
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime(format) + ' UTC'
        except Exception:
            return value  # Return original if formatting fails



    return app

    
if __name__ == '__main__':
    app = create_app()
    check_api_config(app)
    init_admin(app)
    import multiprocessing
    multiprocessing.set_start_method("spawn")
    app.run(debug=True)


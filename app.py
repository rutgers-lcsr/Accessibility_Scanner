from multiprocessing import Process
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
import jwt
from sqlalchemy import inspect
from models import db
from authentication.login import jwt
from models.user import Profile, User
from mail import mail
from werkzeug.security import generate_password_hash
import os

def init_admin(app):
    admin_user = os.environ.get("ADMIN_EMAIL", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")

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

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    CORS(app, supports_credentials=True)

    # Swagger docs
    from flasgger import Swagger
    swagger = Swagger(app)

    mail.init_app(app)
    db.init_app(app)
    migrate = Migrate(app, db)
    jwt.init_app(app)
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
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(domain_bp, url_prefix='/api/domains')
    app.register_blueprint(report_bp, url_prefix='/api/reports')
    app.register_blueprint(sites_bp, url_prefix='/api/sites')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(website_bp, url_prefix='/api/websites')
    app.register_blueprint(scan_bp, url_prefix='/api/scans')
    app.register_blueprint(axe_bp, url_prefix='/api/axe')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')

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

def init_scanner():
    from scanner.queue_process import queue_scanner 
    p = Process(target=queue_scanner)
    p.start()
    p.join()
    
if __name__ == '__main__':
    app = create_app()
    init_admin(app)
    import multiprocessing
    multiprocessing.set_start_method("spawn")
    app.run(debug=True)


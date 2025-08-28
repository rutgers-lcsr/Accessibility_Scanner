from multiprocessing import Process
from flask import Flask
from flask_cors import CORS
import jwt
from importlib.metadata.diagnose import inspect
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
        user = User.query.filter_by(email=admin_user).first()
        if not user:
            try:
                user = User(email=admin_user, password=generate_password_hash(admin_password))
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
    jwt.init_app(app)
    app.static_folder = 'static'

    from blueprints.auth import auth_bp
    from blueprints.domains import domain_bp
    from blueprints.report import report_bp
    from blueprints.sites import sites_bp
    from blueprints.user import user_bp
    from blueprints.website import website_bp
    from blueprints.scan import scan_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(domain_bp, url_prefix='/api/domains')
    app.register_blueprint(report_bp, url_prefix='/api/reports')
    app.register_blueprint(sites_bp, url_prefix='/api/sites')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(website_bp, url_prefix='/api/websites')
    app.register_blueprint(scan_bp, url_prefix='/api/scans')

    with app.app_context():
        inspector = inspect(db.engine)
        # force schema default to db.engine.url.database
        db.metadata.create_all(bind=db.engine, checkfirst=True)
    return app

def init_scanner():
    from scanner.queue_process import queue_scanner 
    p = Process(target=queue_scanner,daemon=True)
    p.start()
    p.join()
    
if __name__ == '__main__':
    app = create_app()
    init_admin(app)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        init_scanner()

    app.run(debug=True)


from flask import Blueprint, jsonify, render_template, request
from config import CLIENT_URL
from flask_jwt_extended import current_user, jwt_required
from models.user import User
from models import db
from models.website import Website
from utils.jwt import decode_jwt_token

user_bp = Blueprint('user', __name__)

@user_bp.route('/me/', methods=['GET'])
@jwt_required()
def get_user():
    user = db.session.get(User, current_user.id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200
    

@user_bp.route('/unsubscribe/', methods=['GET'])
def unsubscribe():
    
    # This token is created in NewWebsiteEmail
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Token is required'}), 400

    payload = decode_jwt_token(token)
    if not payload or payload.get("error") is not None:
        return jsonify({'error': 'Invalid token'}), 401
    if payload.get("action") == "subscribe":
        # Links from before opt-outs were per user; honouring them would silence the
        # whole website, which is what they used to do.
        return jsonify({'error': 'This unsubscribe link is out of date; use the link in a newer email '
                                 'or the notifications switch on the website page'}), 400
    if payload.get("action") != "unsubscribe" or not payload.get("user_id"):
        return jsonify({'error': 'Invalid token'}), 401

    website = db.session.get(Website, payload.get('website_id'))
    user = db.session.get(User, payload.get('user_id'))
    if not website or not user:
        return jsonify({'error': 'Website not found'}), 404

    website.set_subscribed(user, False)

    # The link is opened in a browser, so answer with a page rather than JSON.
    return render_template('unsubscribed.html', website=website, client_url=CLIENT_URL), 200
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
    

def _unsubscribe_target(token):
    """``((user, websites), None)`` for a valid token, else ``(None, (response, status))``.
    A token without a website id covers every website the person is emailed about."""
    if not token:
        return None, (jsonify({'error': 'Token is required'}), 400)
    payload = decode_jwt_token(token)
    if not payload or payload.get("error") is not None:
        return None, (jsonify({'error': 'Invalid token'}), 401)
    if payload.get("action") == "subscribe":
        # Links from before opt-outs were per user; honouring them would silence the
        # whole website, which is what they used to do.
        return None, (jsonify({'error': 'This unsubscribe link is out of date; use the link in a newer email '
                                        'or the notifications switch on the website page'}), 400)
    if payload.get("action") != "unsubscribe" or not payload.get("user_id"):
        return None, (jsonify({'error': 'Invalid token'}), 401)
    user = db.session.get(User, payload.get('user_id'))
    if not user:
        return None, (jsonify({'error': 'Website not found'}), 404)
    if payload.get('website_id') is None:
        from services.owner_digest import member_websites
        websites = member_websites(user)
    else:
        website = db.session.get(Website, payload.get('website_id'))
        if not website:
            return None, (jsonify({'error': 'Website not found'}), 404)
        websites = [website]
    return (user, websites), None


@user_bp.route('/unsubscribe/', methods=['GET'])
def unsubscribe_confirm():
    """The link in an email: shows what will be silenced and asks for a click. Opting out
    happens on POST only, so a mail client that follows links cannot unsubscribe anyone."""
    token = request.args.get('token')
    target, error = _unsubscribe_target(token)
    if error:
        return error
    user, websites = target
    return render_template('unsubscribe_confirm.html', websites=websites, token=token, client_url=CLIENT_URL), 200


@user_bp.route('/unsubscribe/', methods=['POST'])
def unsubscribe():
    """The confirmation form, or a mail client's one-click POST (RFC 8058) with the token
    in the query string."""
    token = request.form.get('token') or request.args.get('token')
    target, error = _unsubscribe_target(token)
    if error:
        return error
    user, websites = target
    for website in websites:
        website.set_subscribed(user, False, commit=False)
    db.session.commit()
    return render_template('unsubscribed.html', websites=websites, client_url=CLIENT_URL), 200

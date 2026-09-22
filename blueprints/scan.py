import base64
from urllib.parse import urlparse, urlunparse

from flask import Blueprint, Response, current_app, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from models.quick_scan import QuickScan
from models.website import Site, Website
from models import db
from scanner.utils.service import check_url
from services.quick_scan import queue_quick_scan, quick_scan_in_progress, quick_scan_state
from services.scan import (
    queue_site_scan,
    queue_website_scan,
    resolve_task_target,
    serialize_task_state,
    site_scan_in_progress,
)
from utils.limiter import limiter
from utils.urls import get_netloc, is_safe_target

scan_bp = Blueprint('scan', __name__)

@scan_bp.route('/scan/', methods=['POST'])
@limiter.limit("5/minute")
@jwt_required()
def scan_website():
    """
    Trigger a website or site scan using Celery background tasks.
    ---
    tags:
        - Scans
    parameters:
        - in: query
          name: website
          type: integer
          description: Website ID to scan
        - in: query
          name: site
          type: integer
          description: Site ID to scan
    responses:
        202:
            description: Scan task queued successfully
        400:
            description: Invalid input
        403:
            description: Unauthorized
        409:
            description: Scan already in progress
    """
    data = request.args
    website = data.get("website", None, str)
    site = data.get("site", None, str)
    
    if not website and not site:
        return jsonify({"error": "No website or site provided"}), 400
    
    try:
        if website:
            # check if we got a full url or website id
            try:
                website_id = int(website)
            except ValueError:
                return jsonify({"error": "Invalid website ID"}), 400

            website_obj = db.session.get(Website, website_id)
            if not website_obj:
                return jsonify({"error": "Website not found"}), 404

            # check current user can scan
            if not website_obj.can_scan(current_user):
                return jsonify({"error": "Unauthorized"}), 403

            task_id, queued = queue_website_scan(website_obj)
            response = {
                "task_id": task_id,
                "status_endpoint": f"/api/scans/status/{task_id}",
                "polling_endpoint": f"/api/scans/status/?website={website_id}",
            }
            if queued:
                response["message"] = "Scan queued successfully"
            else:
                response["info"] = "Scan already in progress"
            return jsonify(response), 202

        if site:
            try:
                site_id = int(site)
            except ValueError:
                return jsonify({"error": "Invalid site ID"}), 400

            site_obj = db.session.get(Site, site_id)
            if not site_obj:
                return jsonify({"error": "Site not found"}), 404

            # check if current user can scan
            if not site_obj.can_scan(current_user):
                return jsonify({"error": "Unauthorized"}), 403

            if site_scan_in_progress(site_obj):
                return jsonify({"error": "Scan already in progress"}), 409

            task_id = queue_site_scan(site_obj)
            return jsonify({
                "message": "Scan queued successfully",
                "task_id": task_id,
                "status_endpoint": f"/api/scans/status/{task_id}",
                "polling_endpoint": f"/api/scans/status/?site={site_id}"
            }), 202

    except Exception:
        current_app.logger.exception("Error queueing scan (website=%s, site=%s)", website, site)
        return jsonify({'error': 'Could not queue the scan'}), 500

    return jsonify({"error": "No valid website or site provided"}), 400

@scan_bp.route('/status/<task_id>', methods=['GET'])
@jwt_required()
def get_task_status(task_id):
    """
    Get the status of a Celery task by its ID.

    Only the task's own website/site owners (or anyone who may view it) can read it.
    ---
    tags:
        - Scans
    parameters:
        - in: path
          name: task_id
          type: string
          required: true
          description: Celery task ID
    responses:
        200:
            description: Task status information
        404:
            description: Task not found (or not visible to this user)
    """
    quick = db.session.query(QuickScan).filter_by(task_id=task_id).first()
    if quick is not None:
        if not quick.can_view(current_user):
            return jsonify({'error': 'Task not found'}), 404
        # Polled every couple of seconds: leave the report and screenshot to the result endpoint.
        return jsonify(serialize_task_state(task_id, light=True)), 200

    target = resolve_task_target(task_id)
    if not target or not target.can_view(current_user):
        return jsonify({'error': 'Task not found'}), 404

    return jsonify(serialize_task_state(task_id)), 200


@scan_bp.route('/quick/', methods=['POST'])
@limiter.limit("5/minute")
@jwt_required()
def start_quick_scan():
    """
    Audit one page ad hoc, without registering a website. Allowed domains only.
    ---
    tags:
        - Scans
    parameters:
        - in: body
          name: body
          required: true
          schema:
              type: object
              properties:
                  url:
                      type: string
                      example: "https://cs.rutgers.edu/people"
    responses:
        202:
            description: task_id, url, status_endpoint (poll) and result_endpoint (read when done).
        400:
            description: Not a public http(s) URL, not under an allowed domain (code not_allowed_domain), or unreachable.
        409:
            description: The caller already has a quick scan running.
    """
    data = request.get_json(silent=True) or {}
    url = str(data.get('url') or '').strip()
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return jsonify({'error': 'A full http(s) URL is required'}), 400
    url = urlunparse(parsed._replace(fragment=''))
    if not is_safe_target(url):
        return jsonify({'error': 'That host is not public'}), 400
    host = get_netloc(url).lower()
    if not Website.find_parent_domain(url):
        return jsonify({'error': f'Quick scans are limited to allowed domains; {host} is not under one',
                        'code': 'not_allowed_domain', 'domain': host}), 400
    if not check_url(url):
        return jsonify({'error': 'The page is not reachable'}), 400
    if quick_scan_in_progress(current_user):
        return jsonify({'error': 'You already have a quick scan running; wait for it to finish'}), 409

    try:
        quick = queue_quick_scan(current_user, url)
    except Exception:
        current_app.logger.exception("Error queueing quick scan of %s", url)
        return jsonify({'error': 'Could not queue the scan'}), 500
    return jsonify({
        'task_id': quick.task_id,
        'url': quick.url,
        'status_endpoint': f"/api/scans/status/{quick.task_id}",
        'result_endpoint': f"/api/scans/quick/{quick.task_id}/",
    }), 202


def _own_quick_scan(task_id):
    quick = db.session.query(QuickScan).filter_by(task_id=task_id).first()
    if quick is None or not quick.can_view(current_user):
        return None
    return quick


@scan_bp.route('/quick/<task_id>/', methods=['GET'])
@jwt_required()
def get_quick_scan(task_id):
    """
    The result of a quick scan (owner or site admin).
    ---
    tags:
        - Scans
    parameters:
        - in: path
          name: task_id
          type: string
          required: true
    responses:
        200:
            description: The result (status completed or failed) without the screenshot, plus photo_url; or state FAILURE with error.
        202:
            description: Still running (state, status).
        404:
            description: No such quick scan for this user.
        410:
            description: The result has expired.
    """
    quick = _own_quick_scan(task_id)
    if quick is None:
        return jsonify({'error': 'Quick scan not found'}), 404
    state = quick_scan_state(quick)
    if state['state'] == 'SUCCESS':
        result = dict(state['result'] or {})
        has_photo = bool(result.pop('photo', None))
        result['photo_url'] = f"/api/scans/quick/{task_id}/photo/" if has_photo else None
        result['task_id'] = task_id
        return jsonify(result), 200
    if state['state'] == 'EXPIRED':
        return jsonify({'error': 'This quick scan result has expired'}), 410
    if 'error' in state:
        return jsonify({'task_id': task_id, 'state': state['state'], 'error': state['error']}), 200
    return jsonify({'task_id': task_id, 'state': state['state'], 'status': state.get('status', '')}), 202


@scan_bp.route('/quick/<task_id>/photo/', methods=['GET'])
@jwt_required()
def get_quick_scan_photo(task_id):
    """
    The screenshot of a finished quick scan, as PNG.
    ---
    tags:
        - Scans
    parameters:
        - in: path
          name: task_id
          type: string
          required: true
    responses:
        200:
            description: PNG bytes.
        404:
            description: No such quick scan, not finished, or no screenshot.
    """
    quick = _own_quick_scan(task_id)
    if quick is None:
        return jsonify({'error': 'Quick scan not found'}), 404
    state = quick_scan_state(quick)
    photo = (state.get('result') or {}).get('photo') if state['state'] == 'SUCCESS' else None
    if not photo:
        return jsonify({'error': 'No screenshot for this quick scan'}), 404
    response = Response(base64.b64decode(photo), mimetype='image/png')
    response.cache_control.private = True
    response.cache_control.max_age = 3600
    return response

@scan_bp.route('/status/', methods=['GET'])
@jwt_required()
def get_scan_status():
    data = request.args
    website = data.get("website", None, int)
    site = data.get("site", None, int)

    if website:
        # website is just an id
        website = db.session.get(Website, website)
        if not website:
            return {"error": "Invalid website URL"}, 400

        # check if current user can view
        if not website.can_view(current_user):
            return {"error": "Unauthorized"}, 403

        if not website.current_task_id:
            website = website.to_dict()
            return jsonify(website), 200

        return jsonify({"scanning": website.current_task_id is not None}), 200

    if site:

        # site is just an id
        site = db.session.get(Site, site)
        if not site:
            return {"error": "Invalid site URL"}, 400
        # check if current user can view
        if not site.can_view(current_user):
            return {"error": "Unauthorized"}, 403
        
        if not site.scanning:
            report = site.get_recent_report()
            return jsonify(report), 200

        return jsonify({"scanning": site.scanning}), 200

    return jsonify({"error": "No valid website or site provided"}), 400
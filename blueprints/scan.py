from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from models.website import Site, Website
from models import db
from services.scan import (
    queue_site_scan,
    queue_website_scan,
    resolve_task_target,
    serialize_task_state,
    site_scan_in_progress,
)
from utils.limiter import limiter

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
    target = resolve_task_target(task_id)
    if not target or not target.can_view(current_user):
        return jsonify({'error': 'Task not found'}), 404

    return jsonify(serialize_task_state(task_id)), 200

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
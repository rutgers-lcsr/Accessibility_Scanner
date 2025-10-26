from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from authentication.login import admin_required
from models.website import Site, Website
from models import db
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import DEBUG
from utils.urls import get_full_url
from scanner.tasks import scan_website as scan_website_task, scan_site as scan_site_task

scan_limiter = Limiter(key_func=get_remote_address)
scan_bp = Blueprint('scan', __name__)

@scan_bp.route('/scan/', methods=['POST'])
@scan_limiter.limit("1/minute" if DEBUG else "5/minute")
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

            # Check if scan is active
            if website_obj.current_task_id:
                
                # Sometimes if app crashes, scanning flag is not reset so check if theres a task in progress
                # check websites task
                website_task = scan_website_task.AsyncResult(website_obj.current_task_id)
                if website_task.state in ['PENDING', 'PROGRESS']:
                    return jsonify({"info": "Scan already in progress", 
                                    "task_id": website_obj.current_task_id, 
                                    "status_endpoint": f"/api/scans/status/{website_task.id}", 
                                    "polling_endpoint": f"/api/scans/status/?website={website_id}" 
                                    }), 202

            # Queue the Celery task
            task = scan_website_task.delay(website_obj.url)
            
            # set the websites current task id
            website_obj.current_task_id = task.id
            db.session.commit()

            return jsonify({
                "message": "Scan queued successfully",
                "task_id": task.id,
                "status_endpoint": f"/api/scans/status/{task.id}",
                "polling_endpoint": f"/api/scans/status/?website={website_id}"
            }), 202

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

            if site_obj.scanning:
                return jsonify({"error": "Scan already in progress"}), 409

            # Queue the Celery task
            task = scan_site_task.delay(site_obj.url)
            
            return jsonify({
                "message": "Scan queued successfully",
                "task_id": task.id,
                "status_endpoint": f"/api/scans/status/{task.id}",
                "polling_endpoint": f"/api/scans/status/?site={site_id}"
            }), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "No valid website or site provided"}), 400

@scan_bp.route('/status/<task_id>', methods=['GET'])
@jwt_required()
def get_task_status(task_id):
    """
    Get the status of a Celery task by its ID.
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
            description: Task not found
    """
    from celery.result import AsyncResult
    from celery_app import celery
    
    task = AsyncResult(task_id, app=celery)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task is waiting to be executed...',
        }
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'status': task.info.get('status', ''),
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'result': task.result,
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'status': str(task.info),  # Exception message
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info),
        }
    
    return jsonify(response), 200

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
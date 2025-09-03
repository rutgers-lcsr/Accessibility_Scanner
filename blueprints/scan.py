import asyncio
import threading
from flask import Flask, Blueprint, jsonify, request
from multiprocessing import Process
from flask_jwt_extended import jwt_required
from authentication.login import admin_required
from models.website import Site, Website
from scanner.scan import run_scan, run_scan_site
from models import db
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import DEBUG
from utils.urls import get_full_url, get_netloc, get_site_netloc
scan_limiter = Limiter(key_func=get_remote_address)
scan_bp = Blueprint('scan', __name__)

current_scans = set()

loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()

async def conduct_scan_website(website: str):

    try:
        website = get_full_url(website)
        process = Process(target=run_scan, args=(website,), daemon=True)
        process.start()
        process.join()
    except Exception as e:
        return {"error": str(e)}, 500
   

async def conduct_scan_site(site: str):

    try:
        site = get_full_url(site)
        process = Process(target=run_scan_site, args=(site,), daemon=True)
        process.start()
        process.join()
    except Exception as e:
        return {"error": str(e)}, 500

@scan_bp.route('/scan/', methods=['POST'])
@scan_limiter.limit("1/minute" if DEBUG else "5/minute")
@admin_required
def scan_website():
    data = request.args
    website = data.get("website", None, str)
    site = data.get("site", None, str)
    print(website, site)
    
    if not website and not site:
        return jsonify({"error": "No website or site provided"}), 400
    try:
        if website:
            # check if we got a full url or website id
            try:
                website_id = int(website)
            except ValueError:
                return {"error": "Invalid website ID"}, 400

            website = db.session.get(Website, website_id)
            if not website:
                return {"error": "Invalid website URL"}, 400
            website_url = f"https://{website.base_url}"

            # Check if scan is active
            if website.scanning:
                return {"error": "Scan already in progress"}, 409

            asyncio.run_coroutine_threadsafe(conduct_scan_website(website_url), loop)
            return jsonify({"message": "Scan started", "polling_endpoint": f"/api/scans/status/?website={website_id}"}), 202

        if site:
            try:
                site_id = int(site)
            except ValueError:
                return {"error": "Invalid site ID"}, 400
            
            site = db.session.get(Site, site_id)
            if not site:
                return {"error": "Invalid site URL"}, 400

            site_url = get_full_url(site.url)

            if site.scanning:
                return {"error": "Scan already in progress"}, 409

            asyncio.run_coroutine_threadsafe(conduct_scan_site(site_url), loop)
            return jsonify({"message": "Scan started", "polling_endpoint": f"/api/scans/status/?site={site_id}"}), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "No valid website or site provided"}), 400

@scan_bp.route('/status/', methods=['GET'])
@admin_required
def get_scan_status():
    data = request.args
    website = data.get("website", None, int)
    site = data.get("site", None, int)

    if website:
        # website is just an id
        website = db.session.get(Website, website)
        if not website:
            return {"error": "Invalid website URL"}, 400

        if not website.scanning:
            website = website.to_dict()
            return jsonify(website), 200

        return jsonify({"scanning": website.scanning}), 200

    if site:

        # site is just an id
        site = db.session.get(Site, site)
        if not site:
            return {"error": "Invalid site URL"}, 400


        if site.scanning:
            report = site.get_recent_report()
            return jsonify(report), 200

        return jsonify({"scanning": site.scanning}), 200

    return jsonify({"error": "No valid website or site provided"}), 400
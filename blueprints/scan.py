import asyncio
from urllib.parse import urlparse
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
scan_limiter = Limiter(key_func=get_remote_address)
scan_bp = Blueprint('scan', __name__)

current_scans = set()



async def conduct_scan_website(website: str, current_scans: set):
    url = urlparse(website)

    website_key = f"{url.netloc}"
    if website_key in current_scans:
        return {"error": "Scan already in progress"}, 409

    current_scans.add(website_key)
    try:
        website = f"{url.scheme}://{url.netloc}"
        process = Process(target=run_scan, args=(website,))
        process.start()
        process.join()
    finally:
        current_scans.remove(website_key)

async def conduct_scan_site(site: str, current_scans: set):
    parsed_url = urlparse(site)
    site_key = f"{parsed_url.netloc}{parsed_url.path}"
    if site_key in current_scans:
        return {"error": "Scan already in progress"}, 409

    current_scans.add(site_key)
    try:
        site = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        process = Process(target=run_scan_site, args=(site,))
        process.start()
        process.join()
    finally:
        current_scans.remove(site_key)


@scan_bp.route('/status', methods=['GET'])
def scan_status():
    return jsonify(list(current_scans)), 200

@scan_bp.route('/scan', methods=['POST'])
@scan_limiter.limit("1/second" if DEBUG else "5/minute")
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
                website_id = None

            if website_id is None and urlparse(website).netloc:
                website_url = f"https://{urlparse(website).netloc}"
            else:
                # site is just an id
                website = db.session.get(Website, website_id)
                if not website:
                    return {"error": "Invalid website URL"}, 400
                website_url = f"https://{website.base_url}"

            asyncio.run(conduct_scan_website(website_url, current_scans))
            return jsonify({"message": "Scan started"}), 202

        if site:
            try:
                site_id = int(site)
            except ValueError:
                site_id = None

            # check if we got a full url or site id
            if site_id is None and urlparse(site).netloc and urlparse(site).path:
                site_url = f"https://{urlparse(site).netloc}{urlparse(site).path}"
            else:
                # site is just an id
                site = db.session.get(Site, site_id)
                if not site:
                    return {"error": "Invalid site URL"}, 400

                url_parse = urlparse(site.url)
                site_url = f"https://{url_parse.netloc}{url_parse.path}"

            asyncio.run(conduct_scan_site(site_url, current_scans))
            
            site = db.session.get(Site, site_id)
            
            report = site.get_recent_report()
            return jsonify(report), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "No valid website or site provided"}), 400

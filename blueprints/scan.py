from urllib.parse import urlparse
from flask import Flask, Blueprint, request
from multiprocessing import Process

from flask_jwt_extended import jwt_required
from authentication.login import admin_required
from models.website import Website
from scanner.scan import run_scan
from models import db
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

scan_limiter = Limiter(key_func=get_remote_address)
scan_bp = Blueprint('scan', __name__)

current_scans = set()



async def conduct_scan_website(website: str):
    url = urlparse(website)

    website_key = f"{url.netloc}"
    if website_key in current_scans:
        return {"error": "Scan already in progress"}, 409

    current_scans.add(website_key)
    try:
        website = f"{url.scheme}://{url.netloc}"
        process = Process(target=run_scan, args=(website,))
        process.start()
        await process.join()
    finally:
        current_scans.remove(website_key)

async def conduct_scan_site(site: str):
    parsed_url = urlparse(site)
    site_key = f"{parsed_url.netloc}{parsed_url.path}"
    if site_key in current_scans:
        return {"error": "Scan already in progress"}, 409

    current_scans.add(site_key)
    try:
        site = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        process = Process(target=run_scan, args=(site,))
        process.start()
        await process.join()
    finally:
        current_scans.remove(site_key)


@scan_bp.route('/status', methods=['GET'])
def scan_status():
    return {"scans_in_progress": list(current_scans)}, 200

@scan_bp.route('/scan', methods=['POST'])
@scan_limiter.limit("5/minute")
@jwt_required()
@admin_required
async def scan_website():
    data = request.args
    website = data.get("website", None, str)
    site = data.get("site", None, str)
    if not website and not site:
        return {"error": "No website or site provided"}, 400


    if website:
        # check if we got a full url or website id
        if urlparse(website).netloc:
            website_url = f"https://{urlparse(website).netloc}"
        else:
            website = db.session.get(Website, website)
            if not website:
                return {"error": "Invalid website URL"}, 400
            website_url = f"https://{website.base_url}"

        return await conduct_scan_website(website_url)

    if site:
        
        return await conduct_scan_site(site)

    url = urlparse(website)
    if url.netloc in current_scans:
        return {"error": "Scan already in progress"}, 409

    return await conduct_scan_website(website)




# Queue processing for scanning websites
# This module handles the background tasks for scanning websites for accessibility issues. Should manage the queue of websites to be scanned and process them in the background. Should be careful of rate limits and not overwhelm the target websites with requests.
import queue
from app import create_app
from scanner.log import log_message
from scanner.scan import run_scan
from multiprocessing import Process
from models import db
from models.website import Website
from config import DEBUG 
from datetime import datetime, timedelta
import time
import schedule

process_q = queue.Queue()


def process_queue():
    app = create_app()
    with app.app_context():
        websites = db.session.query(Website).filter(Website.is_active == True).all()
    
    for website in websites:
        now = datetime.now()
        
        if DEBUG:
            process_q.put(website)
        if website.last_scanned is None or now - website.last_scanned > timedelta(days=website.rate_limit):
            process_q.put(website)

    while not process_q.empty():
        website = process_q.get()
        website_url = f'https://{website.base_url}'
        
        if DEBUG:
            print(f"Processing website for scan: {website_url}")
            continue
        
        p = Process(target=run_scan, args=(website_url,))
        p.start()
        p.join()
    
    log_message("Completed processing website queue", 'info')

def queue_scanner():
    if DEBUG:
        schedule.every().minute.do(process_queue)
    else:
        schedule.every().day.at("00:00").do(process_queue)
    log_message(f"Scheduled website scanning.", 'info')
    while True:
        schedule.run_pending()
        time.sleep(1)

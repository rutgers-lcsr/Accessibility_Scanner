from flask import Flask, render_template
from flask_mail import Message
from config import CLIENT_URL, JWT_SECRET_KEY
import mail
from models.report import Report
from models.website import Website
from datetime import datetime

from utils.jwt import generate_jwt_token
class AccessEmails():
    def __init__(self):
        self.client_url = CLIENT_URL
        self.year = datetime.now().year


class AdminNewWebsiteEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        super().__init__()

    def send(self):
        msg = Message("New Website Added",
                      recipients=[self.website.email])

        msg.html = render_template("emails/admin_new_website.html", website=self.website, client_url=self.client_url)
        mail.send(msg)

class NewWebsiteEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        super().__init__()

    def send(self):
        msg = Message("New Website Added",
                      recipients=[self.website.email])

        jwt_token = generate_jwt_token({"action": "subscribe", "website_id": self.website.id, "email": self.website.email})
        msg.html = render_template("emails/new_website.html", website=self.website, client_url=self.client_url, jwt_token=jwt_token)
        mail.mail.send(msg)

class ScanFinished(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        self.report_counts = website.get_report_counts()
        super().__init__()

    def send(self):
        if not self.website.should_email:
            return
        
        msg = Message("Accessibility Scan Finished",
                      recipients=[self.website.email])

        msg.html = render_template("emails/scan_finished.html", website=self.website, client_url=self.client_url, scan=self.report_counts)
        mail.mail.send(msg)
from operator import or_
from flask import Flask, render_template
from flask_mail import Message
from config import CLIENT_URL, DEBUG, JWT_SECRET_KEY, SITE_ADMINS, TESTING
from mail import mail
from models.report import Report
from models.user import User
from models import db
from models.website import Website
from datetime import datetime

from scanner.log import log_message
from utils.jwt import generate_jwt_token
class AccessEmails():
    def __init__(self):
        self.client_url = CLIENT_URL
        self.year = datetime.now().year

    def send(self):
        if not self.msg:
            raise ValueError("Message not initialized")
        
        if TESTING:
            print("Email content:")
            print("Subject:", self.msg.subject)
            print("To:", self.msg.recipients)
            # print("Body:", self.msg.html)
        try:
            mail.send(self.msg)
        except Exception as e:
            log_message(f"Error sending email: {e}", 'error')


class AdminNewWebsiteEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        super().__init__()

    def send(self):
        admins = []
        for admin in SITE_ADMINS:
            user = db.session.query(User).filter(or_(User.username == admin, User.email == admin)).first()
            if user:
                admins.append(user)

        msg = Message("New Website Added",
                      recipients=[admin.email for admin in admins])

        msg.html = render_template("emails/admin_new_website.html", website=self.website, client_url=self.client_url)
        self.msg = msg
        super().send()
        
class NewWebsiteEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        super().__init__()

    def send(self):
        msg = Message("New Website Added",
                recipients=[self.website.email])

        jwt_token = generate_jwt_token({"action": "subscribe", "website_id": self.website.id, "email": self.website.email})
        msg.html = render_template("emails/new_website.html", website=self.website, client_url=self.client_url, jwt_token=jwt_token)

        self.msg = msg
        super().send()

class ScanFinishedEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        self.report_counts = website.get_report_counts()
        super().__init__()

    def send(self):
        if not self.website.should_email or not self.website.email:
            return

        msg = Message("Accessibility Scan Finished",
                      recipients=[self.website.email])

        msg.html = render_template("emails/scan_finished.html", website=self.website.to_dict(), client_url=self.client_url, scan=self.report_counts, timestamp=datetime.now().isoformat())

        self.msg = msg
        super().send()
from operator import or_
from flask import Flask, render_template
from flask_mail import Message
from config import CLIENT_URL, TESTING
from mail import mail
from models.report import Report
from models.user import User
from models import db
from models.website import Website
from models.user import Profile
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
            log_message(f"Message was not sent", 'info')
            # print("Body:", self.msg.html)
            
            
        # dont send if recipients is localhost
        if any("localhost" in recipient for recipient in self.msg.recipients):
            log_message(f"Email not sent to localhost address: {self.msg.recipients}", 'warning')
            return
        
        try:
            mail.send(self.msg)
            log_message(f"Email sent to {self.msg.recipients}", 'info')
        except Exception as e:
            log_message(f"Error sending email: {e}", 'error')


class AdminNewWebsiteEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        super().__init__()

    def send(self):
        adminsUsers = db.session.query(User).join(User.profile).filter(User.is_active==True, Profile.is_admin==True).all()

        msg = Message("New Website Added",
                      recipients=[admin.email for admin in adminsUsers])

        msg.html = render_template("emails/admin_new_website.html", website=self.website, client_url=self.client_url)
        self.msg = msg
        super().send()
        
class NewWebsiteEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        super().__init__()

    def send(self):
        
        emails = self.website.get_user_emails()
        if not emails:
            log_message(f"Website {self.website.id} has no associated user emails to send new website notification.", 'warning')
            return
        
        msg = Message("New Website Added",
                      recipients=emails)

        jwt_token = generate_jwt_token({"action": "subscribe", "website_id": self.website.id, "email": self.website.email})
        msg.html = render_template("emails/new_website.html", website=self.website, client_url=self.client_url, jwt_token=jwt_token)

        self.msg = msg
        super().send()

class ScanFinishedEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        self.report_counts = website.get_report_counts()
        super().__init__()

    def send(self, email=None, force=False):
        if not force and not self.website.should_email:
            return

        emails = self.website.get_user_emails()
        if email:
            emails.append(email)
        emails = list(set([e for e in emails if e]))
        if not emails:
            log_message(f"Website {self.website.id} has no associated user emails to send scan finished notification.", 'warning')
            return

        msg = Message("Accessibility Scan Finished",
                      recipients=emails)

        msg.html = render_template("emails/scan_finished.html", website=self.website.to_dict(), client_url=self.client_url, scan=self.report_counts, timestamp=datetime.now().isoformat())
        
        if not force:
            # check if we should email based on report counts
            counts = self.report_counts
            should_email = False
            if counts.get('critical', 0) > 0:
                should_email = True
            if counts.get('serious', 0) >= 5:
                should_email = True
            if counts.get('moderate', 0) >= 10:
                should_email = True
            if counts.get('minor', 0) >= 10:
                should_email = True
            if counts.get('total', 0) > 15:
                should_email = True
            if not should_email:
                log_message(f"Scan finished email not sent for website {self.website.id} due to no significant issues found.", 'info')
                log_message(f"Scan counts: {counts}", 'info')
                return

        self.msg = msg
        super().send()
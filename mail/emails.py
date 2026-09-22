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
from datetime import datetime, timedelta, timezone

from scanner.log import log_message
from utils.jwt import generate_jwt_token
class AccessEmails():
    def __init__(self):
        self.client_url = CLIENT_URL
        self.year = datetime.now().year

    def send(self) -> bool:
        """Hand the message to the mail server.

        Returns True when it was sent (or would have been, under TESTING) and False when
        it was skipped or delivery failed, so callers can record the notification.
        """
        if not self.msg:
            raise ValueError("Message not initialized")
        
        if TESTING:
            log_message(f"TESTING: not sending email '{self.msg.subject}' to {self.msg.recipients}", 'info')
            return True

        # dont send if recipients is localhost
        if any("localhost" in recipient for recipient in self.msg.recipients):
            log_message(f"Email not sent to localhost address: {self.msg.recipients}", 'warning')
            return False
        
        try:
            mail.send(self.msg)
            log_message(f"Email sent to {self.msg.recipients}", 'info')
            return True
        except Exception as e:
            log_message(f"Error sending email: {e}", 'error')
            return False

    def send_each(self, messages) -> int:
        """Send one message per recipient over a single connection.

        Used for the emails that carry a personal unsubscribe link. Returns how many
        were sent (or would have been, under TESTING). ``self.msg`` is the last message
        built, so callers and tests can inspect the rendered HTML.
        """
        self.messages = list(messages)
        self.msg = self.messages[-1] if self.messages else None
        if not self.messages:
            return 0

        if TESTING:
            for msg in self.messages:
                log_message(f"TESTING: not sending email '{msg.subject}' to {msg.recipients}", 'info')
            return len(self.messages)

        deliverable = []
        for msg in self.messages:
            if any("localhost" in recipient for recipient in msg.recipients):
                log_message(f"Email not sent to localhost address: {msg.recipients}", 'warning')
            else:
                deliverable.append(msg)

        sent = 0
        try:
            with mail.connect() as connection:
                for msg in deliverable:
                    try:
                        connection.send(msg)
                        sent += 1
                        log_message(f"Email sent to {msg.recipients}", 'info')
                    except Exception as e:
                        log_message(f"Error sending email to {msg.recipients}: {e}", 'error')
        except Exception as e:
            log_message(f"Error connecting to the mail server: {e}", 'error')
        return sent


UNSUBSCRIBE_LINK_DAYS = 90


def _unsubscribe_token(website: Website, user: User) -> str:
    """A personal unsubscribe link for one recipient of one website's emails."""
    return generate_jwt_token({
        "action": "unsubscribe",
        "website_id": website.id,
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(days=UNSUBSCRIBE_LINK_DAYS),
    })


def _mark_notified(website: Website) -> None:
    """Record that the website's admin and users were just emailed."""
    website.last_notified = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.add(website)
    db.session.commit()


class AdminNewWebsiteEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        super().__init__()

    def send(self):
        adminsUsers = db.session.query(User).join(User.profile).filter(User.is_active==True, Profile.is_admin==True).all()

        msg = Message("New Website Added",
                      recipients=[admin.email for admin in adminsUsers])

        msg.html = render_template("emails/admin_new_website.html", year=self.year, website=self.website, client_url=self.client_url)
        self.msg = msg
        super().send()
        
class NewWebsiteEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        super().__init__()

    def send(self):
        recipients = [user for user in self.website.get_recipients() if user.email]
        if not recipients:
            log_message(f"Website {self.website.id} has no associated user emails to send new website notification.", 'warning')
            return

        messages = []
        for user in recipients:
            msg = Message("New Website Added", recipients=[user.email])
            msg.html = render_template(
                "emails/new_website.html", year=self.year, website=self.website,
                client_url=self.client_url, jwt_token=_unsubscribe_token(self.website, user),
            )
            messages.append(msg)

        if self.send_each(messages):
            _mark_notified(self.website)

class ScanFinishedEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        self.report_counts = website.get_report_counts()
        super().__init__()

    def _worth_sending(self) -> bool:
        """Automatic sends only go out when the results are significant."""
        violations = self.report_counts.get('violations', {})
        significant = (
            violations.get('critical', 0) > 0
            or violations.get('serious', 0) >= 5
            or violations.get('moderate', 0) >= 10
            or violations.get('minor', 0) >= 10
            or violations.get('total', 0) > 15
        )
        if not significant:
            log_message(f"Scan finished email not sent for website {self.website.id} due to no significant issues found.", 'info')
            log_message(f"Scan counts: {self.report_counts}", 'info')
        return significant

    def _message(self, address: str, jwt_token: str | None) -> Message:
        msg = Message("Accessibility Scan Finished", recipients=[address])
        msg.html = render_template(
            "emails/scan_finished.html", year=self.year, website=self.website.to_dict(),
            client_url=self.client_url, scan=self.report_counts,
            timestamp=datetime.now().isoformat(), jwt_token=jwt_token,
        )
        return msg

    def send(self, email=None, force=False):
        if not force and not self.website.should_email:
            return
        if not force and not self._worth_sending():
            return

        # One message per recipient, each with a personal unsubscribe link. An address
        # given by hand (the admin's "send to" box) has no account to opt out, so no link.
        targets = [(user.email, _unsubscribe_token(self.website, user))
                   for user in self.website.get_recipients() if user.email]
        if email and email not in {address for address, _ in targets}:
            targets.append((email, None))
        if not targets:
            log_message(f"Website {self.website.id} has no associated user emails to send scan finished notification.", 'warning')
            return

        if self.send_each([self._message(address, token) for address, token in targets]):
            _mark_notified(self.website)

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
from utils.urls import get_netloc
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


def _admin_emails() -> list:
    """Addresses of the active site admins."""
    admins = db.session.query(User).join(User.profile).filter(User.is_active == True, Profile.is_admin == True).all()
    return [admin.email for admin in admins if admin.email]


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
        msg = Message("New Website Added", recipients=_admin_emails())

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
    def __init__(self, website: Website, changes: dict | None = None):
        self.website = website
        self.report_counts = website.get_report_counts()
        if changes is None:
            from services.findings import changes_for_sites  # local import: services import models
            from models.website import Site
            changes = changes_for_sites([row.id for row in website.sites.with_entities(Site.id).all()])
        self.changes = changes
        from services.overview import scan_summary  # local import: services import models
        self.summary = scan_summary(website)
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

    def _subject(self) -> str:
        host = get_netloc(self.website.url)
        status = self.summary.get('status')
        if status in ('unreachable', 'failed'):
            return f"Accessibility scan {status}: {host}"
        violations = self.summary['violations']
        return (f"Accessibility scan finished: {host}: {violations['total']} violations "
                f"({violations['critical']} critical)")

    def _message(self, address: str, jwt_token: str | None, website: dict) -> Message:
        msg = Message(self._subject(), recipients=[address])
        msg.html = render_template(
            "emails/scan_finished.html", year=self.year, website=website,
            client_url=self.client_url, scan=self.report_counts, summary=self.summary,
            changes=self.changes, timestamp=datetime.now().isoformat(), jwt_token=jwt_token,
        )
        return msg

    def send(self, email=None, force=False) -> int:
        """Email the website's people; returns how many messages went out."""
        if not force and not self.website.should_email:
            return 0
        if not force and not self._worth_sending():
            return 0

        # One message per recipient, each with a personal unsubscribe link. An address
        # given by hand (the admin's "send to" box) has no account to opt out, so no link.
        targets = [(user.email, _unsubscribe_token(self.website, user))
                   for user in self.website.get_recipients() if user.email]
        if email and email not in {address for address, _ in targets}:
            targets.append((email, None))
        if not targets:
            log_message(f"Website {self.website.id} has no associated user emails to send scan finished notification.", 'warning')
            return 0

        website = self.website.to_dict()  # once, not per recipient: it walks every page
        sent = self.send_each([self._message(address, token, website) for address, token in targets])
        if sent:
            _mark_notified(self.website)
        return sent


class ScanRegressionEmail(AccessEmails):
    """Sent instead of the scan-finished email when a scan is worse than the previous one
    (services.findings.is_regression). No severity thresholds: a regression is news."""

    def __init__(self, website: Website, changes: dict):
        self.website = website
        self.changes = changes
        super().__init__()

    def send(self, force: bool = False) -> bool:
        if not force and not self.website.should_email:
            return False
        recipients = [user for user in self.website.get_recipients() if user.email]
        if not recipients:
            log_message(f"Website {self.website.id} has no associated user emails to send regression notification.", 'warning')
            return False

        new_total = self.changes.get('new_count', 0)
        subject = f"Accessibility regression on {get_netloc(self.website.url)}: {new_total} new violation{'s' if new_total != 1 else ''}"
        messages = []
        for user in recipients:
            msg = Message(subject, recipients=[user.email])
            msg.html = render_template(
                "emails/scan_regression.html", year=self.year, website=self.website,
                client_url=self.client_url, changes=self.changes,
                jwt_token=_unsubscribe_token(self.website, user),
            )
            messages.append(msg)

        sent = self.send_each(messages) > 0
        if sent:
            _mark_notified(self.website)
        return sent


class AdminDigestEmail(AccessEmails):
    """Weekly system digest to site admins (scanner.tasks.send_admin_digest)."""

    def __init__(self, days: int = 7):
        self.days = days
        super().__init__()

    def send(self) -> bool:
        from services.overview import build_digest  # local import: services import models

        recipients = _admin_emails()
        if not recipients:
            log_message("No active site admins to send the digest to", 'warning')
            return False
        digest = build_digest(self.days)
        if not digest['websites_count']:
            log_message("No websites yet; digest not sent", 'info')
            return False

        msg = Message(f"Weekly accessibility digest: {datetime.now().strftime('%b %d, %Y')}", recipients=recipients)
        msg.html = render_template("emails/admin_digest.html", year=self.year, client_url=self.client_url, digest=digest)
        self.msg = msg
        return super().send()

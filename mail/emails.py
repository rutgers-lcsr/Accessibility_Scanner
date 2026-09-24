from datetime import datetime, timedelta, timezone

from flask import render_template
from flask_mail import Message
from jinja2 import TemplateNotFound

from config import CLIENT_URL, TESTING
from mail import mail
from models import db
from models.user import Profile, User
from models.website import Website
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

BUTTON_STYLE = ("display:inline-block;background:#cc0033;color:#ffffff;padding:10px 24px;"
                "border-radius:4px;text-decoration:none;font-weight:500;margin-top:16px;")


def _unsubscribe_token(website: Website | None, user: User) -> str:
    """A personal unsubscribe link for one recipient: one website's emails, or every
    website of theirs when ``website`` is None (the digest and its List-Unsubscribe)."""
    return generate_jwt_token({
        "action": "unsubscribe",
        "website_id": website.id if website else None,
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(days=UNSUBSCRIBE_LINK_DAYS),
    })


def _unsubscribe_url(token: str) -> str:
    return f"{CLIENT_URL}/api/users/unsubscribe/?token={token}"


def _admin_emails() -> list:
    """Addresses of the active site admins."""
    admins = db.session.query(User).join(User.profile).filter(User.is_active == True, Profile.is_admin == True).all()
    return [admin.email for admin in admins if admin.email]


def _mark_notified(website: Website) -> None:
    """Record that the website's admin and users were just emailed."""
    website.last_notified = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.add(website)
    db.session.commit()


def _render(name: str, **context) -> tuple:
    """The HTML body from emails/<name>.html and the text body from emails/<name>.txt
    (None when the email has no text version)."""
    html = render_template(f"emails/{name}.html", **context)
    try:
        text = render_template(f"emails/{name}.txt", **context)
    except TemplateNotFound:
        text = None
    return html, text


def _personal_message(subject: str, address: str, token, template: str, cc=None, **context) -> Message:
    """One recipient's message: HTML plus a plain-text part and, when the recipient has an
    account (``token``), the unsubscribe link in the footer and the headers mail clients
    turn into an "Unsubscribe" button."""
    unsubscribe_url = _unsubscribe_url(token) if token else None
    html, text = _render(template, unsubscribe_url=unsubscribe_url, button_style=BUTTON_STYLE, **context)
    headers = None
    if unsubscribe_url:
        headers = {'List-Unsubscribe': f'<{unsubscribe_url}>', 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click'}
    return Message(subject, recipients=[address], cc=cc or None, body=text, html=html, extra_headers=headers)


class AdminNewWebsiteEmail(AccessEmails):
    def __init__(self, website: Website):
        self.website = website
        super().__init__()

    def send(self):
        msg = Message("New Website Added", recipients=_admin_emails())
        msg.html = render_template("emails/admin_new_website.html", year=self.year, website=self.website,
                                   client_url=self.client_url, button_style=BUTTON_STYLE)
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

        messages = [
            _personal_message("New Website Added", user.email, _unsubscribe_token(self.website, user), 'new_website',
                              year=self.year, website=self.website, client_url=self.client_url)
            for user in recipients
        ]
        if self.send_each(messages):
            _mark_notified(self.website)


class OwnerDigestEmail(AccessEmails):
    """One person's digest over their websites (services.owner_digest builds it and
    decides who gets one). ``tone`` is first, update, no_change, reminder or escalation."""

    def __init__(self, user, digest: dict, tone: str = 'update', cc=None, address: str | None = None):
        self.user = user
        self.digest = digest
        self.tone = tone
        self.cc = cc
        self.address = address or (user.email if user else None)
        super().__init__()

    def subject(self) -> str:
        websites = self.digest['websites']
        totals = self.digest['totals']
        host = websites[0]['host'] if len(websites) == 1 else f"{len(websites)} websites"
        serious = totals['critical_serious']
        issue = 'issue' if serious == 1 else 'issues'
        if self.tone == 'escalation':
            return f"Action required: {host} still has {serious} critical or serious accessibility {issue}"
        if self.tone == 'reminder':
            return f"Reminder: {host} still has {serious} critical or serious accessibility {issue}"
        if websites and all(w['last_scan_status'] in ('failed', 'unreachable') for w in websites):
            return f"Accessibility scan failed: {host}"
        if self.tone == 'first':
            return f"Accessibility report for {host}: {totals['violations']} issues on {totals['pages_with_issues']} pages"
        if self.tone == 'no_change':
            return f"No change on {host}: {totals['violations']} open accessibility issues"
        return f"{host}: {totals['fixed_since']} fixed, {totals['new_since']} new accessibility issues"

    def send(self) -> bool:
        if not self.address:
            return False
        token = _unsubscribe_token(None, self.user) if self.user else None
        self.msg = _personal_message(self.subject(), self.address, token, 'owner_digest', cc=self.cc,
                                     year=self.year, client_url=self.client_url, digest=self.digest, tone=self.tone)
        return super().send()


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
        msg.html = render_template("emails/admin_digest.html", year=self.year, client_url=self.client_url,
                                   digest=digest, button_style=BUTTON_STYLE)
        self.msg = msg
        return super().send()

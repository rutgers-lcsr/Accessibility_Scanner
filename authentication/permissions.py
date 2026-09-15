from config import SITE_ADMINS


def is_site_admin(email: str) -> bool:
    """True when ``email`` is listed in SITE_ADMINS (case-insensitive, full address only).

    Matching on the local part alone would make ``user`` from any CAS server an admin,
    so the whole address must match.
    """
    if not email:
        return False
    return email.strip().lower() in {admin.strip().lower() for admin in SITE_ADMINS}

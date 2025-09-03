


from config import SITE_ADMINS


def is_site_admin(user:str) -> bool:
    # check if user string contains an email
    if user and "@" in user:
        user_id = user.split("@")[0]
    else:
        user_id = user

    for admin in SITE_ADMINS:
        
        # user match is user id or user email is in admin
        if user == admin or user_id == admin.split("@")[0]:
            return True
    return False

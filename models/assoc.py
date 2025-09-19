from models import db


UserWebsiteAssoc = db.Table(
    'user_website_assoc',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE') , primary_key=True),
    db.Column('website_id', db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), primary_key=True)
)
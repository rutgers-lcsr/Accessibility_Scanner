from datetime import datetime
from . import db
from scanner.browser.report import AccessibilityReport
from sqlalchemy.ext.hybrid import hybrid_property

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'))
    site = db.relationship("Site", back_populates="reports")
    url = db.Column(db.String(200), nullable=False)
    base_url = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    report = db.Column(db.JSON, nullable=False)
    links = db.Column(db.JSON, nullable=False)
    videos = db.Column(db.JSON, nullable=False)
    imgs = db.Column(db.JSON, nullable=False)
    tabable = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __init__(self, data: AccessibilityReport, site_id):
        self.from_dict(data)
        self.site_id = site_id

    @hybrid_property
    def num_of_violations(self):
        violations = self.report.get('violations', [])
        return len(violations)

    @hybrid_property
    def num_of_links(self):
        links = self.links.get('links', [])
        return len(links)

    @hybrid_property
    def num_of_videos(self):
        videos = self.videos.get('videos', [])
        return len(videos)

    @hybrid_property
    def num_of_imgs(self):
        imgs = self.imgs.get('imgs', [])
        return len(imgs)

    def from_dict(self, data: AccessibilityReport):
        self.url = data['url']
        self.base_url = data['base_url']
        self.timestamp = datetime.fromtimestamp(data['timestamp'])
        self.report = data['report']
        self.links = data['links']
        self.videos = data['videos']
        self.imgs = data['imgs']
        self.tabable = data['tabable']

    def to_dict(self):

        return {'id': self.id, 'url': self.url, 'base_url': self.base_url, 'timestamp': self.timestamp, 'report': self.report, 'links': self.links, 'videos': self.videos, 'imgs': self.imgs, 'tabable': self.tabable}
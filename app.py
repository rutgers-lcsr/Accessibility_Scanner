from flask import Flask, request, jsonify
import json
from flask_sqlalchemy import SQLAlchemy
from .scanner.scan import Report as GenReport
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///audit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=False)
    base_url = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    violations = db.Column(db.Text, nullable=False)
    links = db.Column(db.Text, nullable=False)
    videos = db.Column(db.Text, nullable=False)
    imgs = db.Column(db.Text, nullable=False)
    tabable = db.Column(db.Boolean, nullable=False)

    def from_dict(self, data: GenReport):
        self.url = data.url
        self.base_url = data.base_url
        self.timestamp = data.timestamp
        self.violations = str(data.violations)
        self.links = data.links
        self.videos = data.videos
        self.imgs = data.imgs
        self.tabable = data.tabable

    def to_dict(self):
        violations = json.loads(self.violations)
        links = json.loads(self.links)
        videos = json.loads(self.videos)
        imgs = json.loads(self.imgs)

        return {'id': self.id, 'url': self.url, 'base_url': self.base_url, 'timestamp': self.timestamp, 'violations': violations, 'links': links, 'videos': videos, 'imgs': imgs, 'tabable': self.tabable}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
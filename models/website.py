
import datetime
from typing import List, TypedDict

from sqlalchemy import func
from models import db
from sqlalchemy.ext.hybrid import hybrid_method,hybrid_property
from sqlalchemy.orm import Mapped
from models.report import AxeReportCounts, Report, ReportMinimized
from scanner.accessibility.ace import AxeReportKeys
from utils.urls import get_netloc, is_valid_url

class SiteDict(TypedDict):
    id: int
    url: str
    last_scanned: str | None
    website_id: int
    reports: List[ReportMinimized]
    current_report: ReportMinimized | None
    active: bool
    created_at: str
    updated_at: str

class Site(db.Model):
    __tablename__ = 'site'
    __table_args__ = {"schema": "a11y"}

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    url: Mapped[str] = db.Column(db.String(500), nullable=False)
    last_scanned: Mapped[datetime.datetime] = db.Column(db.DateTime, nullable=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('a11y.website.id'))
    reports: Mapped[List[Report]] = db.relationship('Report', back_populates='site', lazy='dynamic' , cascade="all, delete-orphan")
    active: Mapped[bool] = db.Column(db.Boolean, default=True)
    scanning: Mapped[bool] = db.Column(db.Boolean, default=False)
    created_at: Mapped[datetime.datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime.datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    @hybrid_method
    def get_recent_report(self) -> ReportMinimized | None:
        report = self.reports.order_by(Report.timestamp.desc()).with_entities(Report.id, Report.url, Report.report_counts, Report.timestamp).first()
        report = {
            'id': report.id,
            'url': report.url,
            'report_counts': report.report_counts,
            'timestamp': report.timestamp.isoformat() if report.timestamp else None
        }
        return report



    @hybrid_property
    def public(self) -> bool:
        return self.website.public if self.website else False

    @public.expression
    def public(cls):
        from sqlalchemy import select
        return (
            select(Website.public)
            .where(Website.id == cls.website_id)
            .scalar_subquery()
        )

    def to_dict(self) -> SiteDict:


        reports = self.reports.order_by(Report.timestamp.desc()).limit(5).with_entities(Report.id, Report.url, Report.report_counts, Report.timestamp).all()
    
        return {
            'id': self.id,
            'url': self.url,
            'last_scanned': self.last_scanned.isoformat() if self.last_scanned else None,
            'website_id': self.website_id,
            'reports': [{
                'id': report.id,
                'report_counts': report.report_counts,
                'timestamp': report.timestamp.isoformat() if report.timestamp else None,
                'url': report.url
            } for report in reports],
            'current_report': self.get_recent_report(),
            'active': self.active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __init__(self, url, website_id):
        if not is_valid_url(url):
            raise ValueError("Invalid URL")
        self.url = url
        self.website_id = website_id

class WebsiteDict(TypedDict,total=False):
    id: int
    base_url: str
    domain_id: int
    sites: List[int]
    last_scanned: datetime.datetime | None
    report_counts: dict[AxeReportKeys, AxeReportCounts]
    active: bool
    rate_limit: int
    public: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

class Website(db.Model):
    __tablename__ = 'website'
    __table_args__ = {"schema": "a11y"}
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    base_url: Mapped[str] = db.Column(db.String(255), nullable=False)
    domain_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('a11y.domains.id'),)
    # domain: Mapped['Domains'] = db.relationship('Domains', backref='websites', lazy=True)
    sites: Mapped[List['Site']] = db.relationship('Site', backref='website', lazy='dynamic', cascade="all, delete-orphan")
    last_scanned: Mapped[datetime.datetime] = db.Column(db.DateTime, nullable=True)
    # Rate limiting the automatic scanning, in days
    rate_limit: Mapped[int] = db.Column(db.Integer, default=30)
    active: Mapped[bool] = db.Column(db.Boolean, default=False)
    email: Mapped[str] = db.Column(db.String(255), nullable=True)
    should_email: Mapped[bool] = db.Column(db.Boolean, default=True)
    # Whether the website reports are public 
    public: Mapped[bool] = db.Column(db.Boolean, default=False)
    scanning: Mapped[bool] = db.Column(db.Boolean, default=False)
    created_at: Mapped[datetime.datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime.datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


    @hybrid_method
    def is_active(self) -> bool:
        # website is active if a domain doesnt exist and the website is active, or if a domain exists and is active
        return (self.domain and self.domain.active and self.active) or (not self.domain and self.active)

    @is_active.expression
    def is_active(cls):
        return (cls.domain.has(Domains.active == True) & cls.active) | (cls.domain == None & cls.active)

    @hybrid_method
    def get_report_counts(self) -> AxeReportCounts | None:
        sites = self.sites.all()
        if not sites:
            sites = []

        total_counts = {
            'violations': {'total': 0, 'critical': 0, 'serious': 0, 'moderate': 0, 'minor': 0},
            'inaccessible': {'total': 0, 'critical': 0, 'serious': 0, 'moderate': 0, 'minor': 0},
            'incomplete': {'total': 0, 'critical': 0, 'serious': 0, 'moderate': 0, 'minor': 0},
            'passes': {'total': 0, 'critical': 0, 'serious': 0, 'moderate': 0, 'minor': 0}
        }

        for site in sites:
            current_report = site.get_recent_report()
            if current_report and 'report_counts' in current_report:
                for key in total_counts:
                    for subkey in total_counts[key]:
                        total_counts[key][subkey] += current_report['report_counts'][key][subkey]

        return total_counts

    def to_dict(self)-> WebsiteDict:
        return {
            'id': self.id,
            'base_url': self.base_url,
            'sites': [site.id for site in self.sites.with_entities(Site.id).all()],
            'domain_id': self.domain_id,
            'email': self.email,
            'should_email': self.should_email,
            'last_scanned': self.last_scanned.isoformat() if self.last_scanned else None,
            'report_counts': self.get_report_counts(),
            'active': self.is_active(),
            'rate_limit': self.rate_limit,
            'public': self.public,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __init__(self, url, email=None):
        self.base_url =  get_netloc(url)
        self.email = email

    def __repr__(self):
        return f'<Website {self.base_url}>'


# Domains can only be created by the admins
class Domains(db.Model):
    __tablename__ = 'domains'
    __table_args__ = {"schema": "a11y"}
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(200), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('a11y.domains.id'), nullable=True)
    parent = db.relationship('Domains', remote_side=[id], backref='subdomains', lazy=True, post_update=True)
    websites = db.relationship('Website', backref='domain', lazy=True, cascade="all, delete-orphan")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    @hybrid_method
    def part_of_domain(self, url):
        try:
            netloc =  get_netloc(url)
        except ValueError:
            return False
       
        return netloc.endswith(self.domain)

    def to_dict(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'parent': self.parent.to_dict() if self.parent else None,
            'active': self.active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    def __repr__(self):
        return f'<Domain {self.domain}>'

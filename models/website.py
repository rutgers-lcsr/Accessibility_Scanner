
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

Site_Website_Assoc = db.Table(
    'site_website_assoc',
    db.Column('site_id', db.Integer, db.ForeignKey('site.id'), primary_key=True),
    db.Column('website_id', db.Integer, db.ForeignKey('website.id'), primary_key=True)
)


class Site(db.Model):
    __tablename__ = 'site'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    url: Mapped[str] = db.Column(db.String(500), nullable=False)
    last_scanned: Mapped[datetime.datetime] = db.Column(db.DateTime, nullable=True)
    websites: Mapped[List['Website']] = db.relationship('Website', secondary=Site_Website_Assoc, back_populates='sites', lazy='dynamic',cascade="all, delete-orphan")
    reports: Mapped[List['Report']] = db.relationship('Report', back_populates='site', lazy='dynamic' , cascade="all, delete-orphan")
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
    def user_id(self) -> int | None:
        return self.websites

    @user_id.expression
    def user_id(cls):
        from sqlalchemy import select
        return (
            select(Website.user_id)
            .where(Website.id == cls.website_id)
            .scalar_subquery()
        )

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

    def __init__(self, url, website:'Website'| None=None):
        if not is_valid_url(url):
            raise ValueError("Invalid URL")

        self_check = db.session.query(Site).filter_by(url=url).first()
        if self_check:
            if website not in self_check.websites:
                self_check.websites.append(website)
                db.session.add(self_check)
                return self_check
            else:
                raise ValueError("Site already exists")

        self.url = url
        self.websites.append(website)

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
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    url: Mapped[str] = db.Column(db.String(500), nullable=True)
    subdomain_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('subdomains.id'), nullable=False)
    sites: Mapped[List['Site']] = db.relationship('Site', secondary=Site_Website_Assoc, back_populates='websites', lazy='dynamic', cascade="all, delete-orphan")
    last_scanned: Mapped[datetime.datetime] = db.Column(db.DateTime, nullable=True)
    # Rate limiting the automatic scanning, in days
    rate_limit: Mapped[int] = db.Column(db.Integer, default=30)
    active: Mapped[bool] = db.Column(db.Boolean, default=False)
    email: Mapped[str] = db.Column(db.String(255), nullable=True)
    should_email: Mapped[bool] = db.Column(db.Boolean, default=True)
    # Whether the website reports are public 
    public: Mapped[bool] = db.Column(db.Boolean, default=False)
    scanning: Mapped[bool] = db.Column(db.Boolean, default=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime.datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime.datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


    @hybrid_method
    def is_active(self) -> bool:
        # website is active if a subdomain doesnt exist and the website is active, or if a subdomain exists and is active
        return (self.subdomain and self.subdomain.is_active and self.active) or (not self.subdomain and self.active)

    @is_active.expression
    def is_active(cls):
        return (cls.subdomain.has(SubDomain.is_active == True) & cls.active) | (cls.subdomain == None & cls.active)

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
            'subdomain_id': self.subdomain_id,
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

    def __init__(self, url, email=None, user_id=None):
        if not is_valid_url(url):
            raise ValueError("Invalid URL")

        # check if website exists
        website_check = Website.query.filter_by(url=url).first()
        if website_check:
            raise ValueError("Website already exists")

        # find associated subdomain
        subdomain = get_netloc(url)
        subdomain_obj = SubDomain.query.filter_by(subdomain=subdomain).first()
        if subdomain_obj is None:
            # create a subdomain if it doesnt exist
            subdomain_obj = SubDomain(subdomain=subdomain)
            db.session.add(subdomain_obj)

        self.url = url
        self.email = email
        self.user_id = user_id
        self.subdomain = subdomain_obj
        
        


    def __repr__(self):
        return f'<Website {self.base_url}>'


class SubDomain(db.Model):
    __tablename__ = 'subdomains'
    id = db.Column(db.Integer, primary_key=True)
    subdomain = db.Column(db.String(200), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)
    websites = db.relationship('Website', backref='subdomain', lazy=True, cascade="all, delete-orphan")
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    @hybrid_method
    def is_active(self) -> bool:
        return self.domain and self.domain.active
    @is_active.expression
    def is_active(cls):
        return cls.domain.has(Domains.active == True)

    def __init__(self, subdomain:str, domain: 'Domains'=None):
        if not is_valid_url(f"http://{subdomain}"):
            raise ValueError("Invalid subdomain")

        # Check if subdomain is part of a of domain
        if domain and not subdomain.endswith(domain.domain):
            raise ValueError("Subdomain does not match the given domain")

        # make sure subdomain is unique
        subdomain_check = db.session.query(SubDomain).filter_by(subdomain=subdomain).first()
        if subdomain_check:
            raise ValueError("Subdomain already exists")
        

        self.subdomain = subdomain

        if domain:
            self.domain = domain
        else:
            # find a domain for the subdomain
            domain_obj = db.session.query(Domains).filter(func.endswith(Domains.domain, subdomain), Domains.active).first()
            if not domain_obj:
                raise ValueError("No active domain found for the given subdomain. Please contact the administrator to add the domain.")
            self.domain = domain_obj



# Domains can only be created by the admins
class Domains(db.Model):
    __tablename__ = 'domains'
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(200), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=True)
    parent = db.relationship('Domains', remote_side=[id], backref='subdomains', lazy=True, post_update=True)
    subdomains = db.relationship('SubDomain', backref='domain', lazy=True, cascade="all, delete-orphan")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    

    def __init__(self, domain, parent=None):
        if not is_valid_url(f"http://{domain}"):
            raise ValueError("Invalid domain")
        self.domain = domain
        self.parent = parent

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

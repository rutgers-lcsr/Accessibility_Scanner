
from datetime import datetime
from typing import List, TypedDict
from sqlalchemy import func
from models import db
from sqlalchemy.ext.hybrid import hybrid_method,hybrid_property
from sqlalchemy.orm import Mapped
from models.report import AxeReportCounts, Report, ReportMinimized
from models.user import User
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
    last_scanned: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    websites: Mapped[List['Website']] = db.relationship('Website', secondary=Site_Website_Assoc, back_populates='sites', lazy='dynamic')
    reports: Mapped[List['Report']] = db.relationship('Report', back_populates='site', lazy='dynamic' , cascade="all, delete-orphan")
    active: Mapped[bool] = db.Column(db.Boolean, default=True)
    scanning: Mapped[bool] = db.Column(db.Boolean, default=False)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

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
            'websites': [website.id for website in self.websites],
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

    def __init__(self, url, website:'Website' =None):
        if not is_valid_url(url):
            raise ValueError("Invalid URL")

        self_check = db.session.query(Site).filter_by(url=url).first()
        if self_check:
            raise ValueError("Site already exists")

        self.url = url
        if website:
            if website not in self.websites:
                self.websites.append(website)
        

class WebsiteDict(TypedDict,total=False):
    id: int
    base_url: str
    domain_id: int
    sites: List[int]
    last_scanned: datetime | None
    report_counts: dict[AxeReportKeys, AxeReportCounts]
    active: bool
    rate_limit: int
    public: bool
    created_at: datetime
    updated_at: datetime

class Website(db.Model):
    __tablename__ = 'website'
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    url: Mapped[str] = db.Column(db.String(500), nullable=True)
    domain_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)
    sites: Mapped[List['Site']] = db.relationship('Site', secondary=Site_Website_Assoc, back_populates='websites', lazy='dynamic')
    last_scanned: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    # Rate limiting the automatic scanning, in days
    rate_limit: Mapped[int] = db.Column(db.Integer, default=30)
    active: Mapped[bool] = db.Column(db.Boolean, default=False)
    should_email: Mapped[bool] = db.Column(db.Boolean, default=True)
    # Whether the website reports are public 
    public: Mapped[bool] = db.Column(db.Boolean, default=False)
    scanning: Mapped[bool] = db.Column(db.Boolean, default=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user: Mapped['User'] = db.relationship('User', back_populates='websites', lazy=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())



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
            'url': self.url,
            'sites': [site.id for site in self.sites.with_entities(Site.id).all()],
            'domain_id': self.domain_id,
            'email': self.user.email or None if self.user else None,
            'should_email': self.should_email,
            'last_scanned': self.last_scanned.isoformat() if self.last_scanned else None,
            'report_counts': self.get_report_counts(),
            'active': self.active,
            'rate_limit': self.rate_limit,
            'public': self.public,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __init__(self, url:str, user_id:int=None):
        if not is_valid_url(url):
            raise ValueError("Invalid URL")

        # check if website exists
        website_check = db.session.query(Website).filter_by(url=url).first()
        if website_check:
            raise ValueError("Website already exists")
        
        # check if user exists
        user_check = db.session.query(User).filter_by(id=user_id).first()
        if not user_check:
            raise ValueError("User does not exist")

        website_domain = get_netloc(url)
        # make sure a domain exist that is active
        parent_domain = (
            db.session.query(Domain)
            .filter(func.lower(func.trim(website_domain)).endswith(func.lower(func.trim(Domain.domain))))
            .filter(Domain.active == True)
            .order_by(func.length(Domain.domain).desc())
            .first()
        )
        if not parent_domain:
            raise ValueError("No active parent domain found, an administrator must add it first")

        # find associated subdomain if it exists 
        subdomain_obj = db.session.query(Domain).filter_by(domain=website_domain).first()
        if subdomain_obj is None:
            # create a subdomain if it doesnt exist
            subdomain_obj = Domain(domain=website_domain)
            db.session.add(subdomain_obj)

        self.url = url
        self.user_id = user_id
        self.domain = subdomain_obj


    def delete(self, delete_domain: bool = True):

        for site in self.sites:
            websites = site.websites.all()
            if len(websites) <= 1:
                db.session.delete(site)
                Site_Website_Assoc.delete().where(Site_Website_Assoc.c.site_id == site.id)
            else:
                site.websites.remove(self)
                db.session.add(site)

        if delete_domain and len(self.domain.websites) <= 1:
            self.domain.delete()

        Site_Website_Assoc.delete().where(Site_Website_Assoc.c.website_id == self.id)

        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return f'<Website {self.url}>'


# Domains can only be created by the admins
class Domain(db.Model):
    __tablename__ = 'domains'
    id = db.Column(db.Integer, primary_key=True)
    parent_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=True)
    parent: Mapped['Domain'] = db.relationship('Domain', remote_side=[id], backref='children', lazy=True, post_update=True)
    domain: Mapped[str] = db.Column(db.String(200), nullable=False)
    websites: Mapped[List['Website']] = db.relationship('Website', backref='domain', lazy=True, cascade="all, delete-orphan")
    active: Mapped[bool] = db.Column(db.Boolean, default=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


    def __init__(self, domain:str):
        if not is_valid_url(f"http://{domain}"):
            raise ValueError("Invalid domain")


        domain_check = db.session.query(Domain).filter_by(domain=domain).first()
        if domain_check:
            raise ValueError("Domain already exists")

        subdomains = db.session.query(Domain).filter(Domain.domain.endswith(domain)).all()
        if len(subdomains) > 0:
            # all these domains need to be made into subdomains
            for subdomain in subdomains:
                if subdomain.parent and len(subdomain.parent.domain) > len(domain):
                    # if the parent domain is longer than the current domain, skip it
                    # that means the parent domain is a subdomain of the current domain
                    continue

                subdomain.parent = self
                db.session.add(subdomain)                 

        self.domain = domain

        # find parent
        domains = db.session.query(Domain).filter(func.cast(domain, db.String).contains(Domain.domain), Domain.domain != domain).order_by(func.length(Domain.domain).desc()).first()
        if domains:
            if domains.domain != domain:
                self.parent = domains
    
    def delete(self):
        if self.parent:
            for child in self.children:
                child.parent = self.parent
                db.session.add(child)
        for website in self.websites:
            website.delete(delete_domain=False)
        db.session.delete(self)
        db.session.commit()

    @hybrid_method
    def part_of_domain(self, url):
        try:
            netloc =  get_netloc(url)
        except ValueError:
            return False
       
        return netloc.endswith(self.domain)

    def deactivate(self):
        self.active = False
        for website in self.websites:
            website.deactivate()
        for child in self.children:
            child.deactivate()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'parent': self.parent.to_dict() if self.parent else None,
            'websites': [website.id for website in self.websites],
            'active': self.active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    def __repr__(self):
        return f'<Domain {self.domain}>'

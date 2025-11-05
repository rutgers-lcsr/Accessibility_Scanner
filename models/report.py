from datetime import datetime, timezone
from select import select
from typing import List, TypedDict
from sqlalchemy import LargeBinary
from sqlalchemy.dialects.mysql import LONGBLOB

from models.user import User

from . import db
from scanner.browser.report import AccessibilityReport
from scanner.accessibility.ace import AxeReport, AxeReportKeys, AxeResult
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm import Mapped
class AxeReportCounts(TypedDict, total=False):
    total: int
    critical: int
    serious: int
    moderate: int
    minor: int

class ReportMinimized(TypedDict):
    id: int
    url: str
    site_id: int
    report_counts:dict[AxeReportKeys, AxeReportCounts]
    timestamp: str

class ReportDict(TypedDict):
    id: int
    url: str
    site_id: int
    base_url: str
    timestamp: str
    report: AxeReport
    report_counts: dict[AxeReportKeys, AxeReportCounts]
    links: List[str]
    videos: List[str]
    imgs: List[str]
    tabable: bool
    created_at: str
    updated_at: str
    

class Report(db.Model):
    __tablename__ = 'report'
    
    id: Mapped[str] = db.Column(db.Integer, primary_key=True)
    site_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('site.id'))
    site = db.relationship("Site", back_populates="reports")
    error: Mapped[str | None] = db.Column(db.String(255), nullable=True)
    response_code: Mapped[int | None] = db.Column(db.Integer, nullable=True)
    url: Mapped[str] = db.Column(db.String(255), nullable=False)
    base_url: Mapped[str] = db.Column(db.String(255), nullable=False)
    timestamp: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    report: AxeReport = db.Column(db.JSON, nullable=False)
    report_counts: Mapped[dict[AxeReportKeys, AxeReportCounts]] = db.Column(db.JSON, nullable=False)
    links: Mapped[List[str]] = db.Column(db.JSON, nullable=False)
    videos: Mapped[List[str]] = db.Column(db.JSON, nullable=False)
    imgs: Mapped[List[str]] = db.Column(db.JSON, nullable=False)
    tabable: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    photo: Mapped[bytes] = db.Column(LargeBinary(2**32 -1), nullable=True)
    tags: Mapped[List[str]] = db.Column(db.JSON, nullable=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f"<Report {self.id} for site {self.site_id} - {self.url}>"
    def __init__(self, data: AccessibilityReport, site_id):
        self.from_dict(data)
        self.site_id = site_id
        
    @hybrid_method
    def get_date_iso(self, property):
        return property.strftime("%Y-%m-%dT%H:%M:%SZ") if property else None

    @hybrid_property
    def public(self):
        return self.site.public if self.site else False

    @hybrid_property
    def admin_id(self):
        return self.site.websites[0].admin_id if self.site and self.site.websites else None

    @admin_id.expression
    def admin_id(cls):
        from sqlalchemy import select
        from models.website import Site
        return (
            select(Site.admin_id)
            .where(Site.id == cls.site_id)
            .scalar_subquery()
        )

    @hybrid_method
    def can_view(self, user: User) -> bool:
        if self.public:
            return True
        if not user:
            return False
        if user.profile.is_admin:
            return True
        if self.site.can_view(user):
            return True
        return False

    @can_view.expression
    def can_view(cls, user: User):
        from sqlalchemy import select, case, exists, literal
        from models.website import Site, UserWebsiteAssoc, Website

        # Subquery: does the user have access to any website for this site?
        user_has_access = exists().where(
            UserWebsiteAssoc.c.website_id.in_(
                select(Website.id).where(Website.sites.any(Site.id == cls.site_id))
            ) & (UserWebsiteAssoc.c.user_id == user.id)
        )

        # Subquery: get admin_id for website of this site
        is_admin = exists().where(
            Website.id.in_(
                select(Website.id).where(Website.sites.any(Site.id == cls.site_id))
            ) & (Website.admin_id == user.id)
        )

        return case(
            (cls.public == True, literal(True)),
            (user == None, literal(False)),
            (user.profile.is_admin == True, literal(True)),
            (user_has_access, literal(True)),
            (is_admin, literal(True)),
            else_=literal(False)
        )

    @public.expression
    def public(cls):
        from sqlalchemy import select
        from models.website import Site
        return (
            select(Site.public)
            .where(Site.id == cls.site_id)
            .scalar_subquery()
        )

    def _count_axe(self,type: AxeReportKeys, impact: str| None) -> int:
        axereportList:List[AxeResult] = self.report.get(type, [])

        if impact is None:
            return len(axereportList)

        return sum(1 for v in axereportList if v.get('impact') == impact)


    @hybrid_property
    def num_of_links(self):
        links = self.links.get('links', [])
        return len(links)


    def from_dict(self, data: AccessibilityReport):
        self.url = data['url']
        self.error = data.get('error', None)
        self.response_code = data.get('response_code', None)
        self.base_url = data.get('base_url', '')
        self.timestamp = datetime.fromisoformat(data['timestamp']).replace(tzinfo=timezone.utc)
        self.report = data['report']
        self.report_counts = {
            'violations': {
                'total': self._count_axe("violations", None),
                'critical': self._count_axe("violations", "critical"),
                'serious': self._count_axe("violations", "serious"),
                'moderate': self._count_axe("violations", "moderate"),
                'minor': self._count_axe("violations", "minor")
            },
            "inaccessible": {
                'total': self._count_axe("inaccessible", None),
                'critical': self._count_axe("inaccessible", "critical"),
                'serious': self._count_axe("inaccessible", "serious"),
                'moderate': self._count_axe("inaccessible", "moderate"),
                'minor': self._count_axe("inaccessible", "minor")
            },
            "incomplete": {
                'total': self._count_axe("incomplete", None),
                'critical': self._count_axe("incomplete", "critical"),
                'serious': self._count_axe("incomplete", "serious"),
                'moderate': self._count_axe("incomplete", "moderate"),
                'minor': self._count_axe("incomplete", "minor")
            },
            "passes": {
                'total': self._count_axe("passes", None),
                'critical': self._count_axe("passes", "critical"),
                'serious': self._count_axe("passes", "serious"),
                'moderate': self._count_axe("passes", "moderate"),
                'minor': self._count_axe("passes", "minor")
            }
        }
        self.links = data['links']
        self.videos = data['videos']
        self.imgs = data['imgs']
        self.tabable = data['tabable']
        self.photo = data['photo']
        self.tags = data.get('tags', [])
    def generate_pdf(self) -> bytes:
        from utils.pdf import generate_pdf
        pdf_data = generate_pdf(self)
        return pdf_data

    def to_dict_without_report(self):
           return {
            'id': self.id,
            'url': self.url,
            'site_id': self.site_id,
            'base_url': self.base_url,
            'timestamp': self.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'report_counts': self.report_counts,
            'links': self.links,
            'videos': self.videos,
            'imgs': self.imgs,
            'tabable': self.tabable,
            'tags': self.tags,
            'created_at': self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'updated_at': self.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
           
    def to_dict(self):

        return {
            'id': self.id,
            'url': self.url,
            'base_url': self.base_url,
            'site_id': self.site_id,
            'timestamp': self.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'report': self.report,
            'report_counts': self.report_counts,
            'links': self.links,
            'videos': self.videos,
            'imgs': self.imgs,
            'tabable': self.tabable,
            'tags': self.tags,
        }
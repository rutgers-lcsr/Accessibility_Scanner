
import re
from models import db
from sqlalchemy.orm import Mapped
from datetime import datetime
from typing import List, Literal
import json

from utils.javascript import is_single_arrow_function, is_valid_js, is_valid_object
from utils.urls import is_valid_url

impact_levels = Literal["minor", "moderate", "serious", "critical"]

class Check(db.Model):
    __tablename__ = 'checks'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(255), nullable=False, unique=True)
    evaluate: Mapped[str] = db.Column(db.Text, nullable=False)  # JavaScript function as string
    options: Mapped[str] = db.Column(db.Text, nullable=True)  # JSON string
    pass_text: Mapped[str] = db.Column(db.Text, nullable=False)
    fail_text: Mapped[str] = db.Column(db.Text, nullable=False)
    incomplete_text: Mapped[str] = db.Column(db.Text, nullable=False)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    json: Mapped[str] = db.Column(db.Text, nullable=True)  # Store the full check as JSON for reference
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    def __init__(self, name, evaluate, options=None, pass_text="", fail_text="", incomplete_text=""):
        self.name = name
        self.evaluate = evaluate
        self.options = options
        self.pass_text = pass_text
        self.fail_text = fail_text
        self.incomplete_text = incomplete_text
        self.json = None  # will be set in save()

    def save(self):
        self.validate()

        db.session.add(self)
        db.session.commit()
    
    def validate(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("name cannot be empty")
        
        # Check if check with same name exists
        check_checks = db.session.query(Check).filter_by(name=self.name).first()
        if check_checks and check_checks.id != self.id:
            raise ValueError("Check with this name already exists")
        
        
        # remove comments from evaluate
        self.evaluate = re.sub(r'/\*.*?\*/', '', self.evaluate, flags=re.DOTALL)  # remove /* */ comments
        self.evaluate = re.sub(r'//.*?$', '', self.evaluate, flags=re.MULTILINE)  # remove // comments
        self.evaluate = self.evaluate.strip()
        
        if not is_single_arrow_function(self.evaluate, ["node", "options?", "virtualNode?"], optional_async_function=True):
            raise ValueError("evaluate must be a valid JavaScript function starting with '(node, options?, virtualNode?) => ' and be of type (node: Element, options?: any, virtualNode?: any) => boolean")
        
        if self.options:
            try:
                json.loads(self.options)
            except json.JSONDecodeError:
                raise ValueError("options must be a valid JSON string")
        
        self.pass_text = self.pass_text.strip()
        self.fail_text = self.fail_text.strip()
        self.incomplete_text = self.incomplete_text.strip()

        self.to_js_object(update=True)
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "evaluate": self.evaluate,
            "options": json.loads(self.options) if self.options else None,
            "pass_text": self.pass_text,
            "fail_text": self.fail_text,
            "incomplete_text": self.incomplete_text,
            "created_at": self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": self.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
    def from_json(self, data):
        self.name = data.get("name", self.name)
        self.evaluate = data.get("evaluate", self.evaluate)
        options = data.get("options", None)
        if options is not None:
            self.options = json.dumps(options)
        self.pass_text = data.get("passText", self.pass_text)
        self.fail_text = data.get("failText", self.fail_text)
        self.incomplete_text = data.get("incompleteText", self.incomplete_text)
        
        return self

    def to_json(self):
        json_check = {
            "name": self.name,
            "evaluate": self.evaluate,
            "options": json.loads(self.options) if self.options else None,
            "pass_text": self.pass_text,
            "fail_text": self.fail_text,
            "incomplete_text": self.incomplete_text,
        }

        return json_check

    def to_js_object(self, update=False, force=False) -> str:
        """
        Covert the Check to a JavaScript object string for use in axe-core configuration.
        If update is True, it will update the json field in the database. If force is True, it will commit the change immediately.
        """
        
        
        if not update:
            return self.json if self.json else self.to_js_object(update=True, force=True)
        js_object = f"""
            {{
                id: "{self.name}",
                evaluate: {self.evaluate},
                options: {self.options if self.options else '{}'},
                metadata: {{
                    messages: {{
                        pass: "{self.pass_text}",
                        fail: "{self.fail_text}",
                        incomplete: "{self.incomplete_text}",
                    }}
                }},
            }}
        """ 
        
        is_valid = is_valid_object(js_object)
        
        if not is_valid:
            raise ValueError("Generated JavaScript object is not valid, please check the check fields for invalid characters.")
        
        if update:
            self.json = js_object
            if force:
                db.session.add(self)
                db.session.commit()
            
        return js_object


RuleChecks = db.Table('rule_checks', db.Model.metadata,
    db.Column('rule_id', db.Integer, db.ForeignKey('rules.id'), primary_key=True),
    db.Column('check_id', db.Integer, db.ForeignKey('checks.id'), primary_key=True)
)

RuleChecksAll = db.Table('rule_checks_all', db.Model.metadata,
    db.Column('rule_id', db.Integer, db.ForeignKey('rules.id'), primary_key=True),
    db.Column('check_id', db.Integer, db.ForeignKey('checks.id'), primary_key=True)
)

RuleChecksNone = db.Table('rule_checks_none', db.Model.metadata,
    db.Column('rule_id', db.Integer, db.ForeignKey('rules.id'), primary_key=True),
    db.Column('check_id', db.Integer, db.ForeignKey('checks.id'), primary_key=True)
)   


class Rule(db.Model):
    __tablename__ = 'rules'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    # name to be set as id for axe rule 
    name: Mapped[str] = db.Column(db.String(255), nullable=False, unique=True)
    selector: Mapped[str] = db.Column(db.String(255), nullable=False, default='*')
    exclude_hidden: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=True)
    enabled: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=True)
    matches: Mapped[str] = db.Column(db.String(255), nullable=True)
    description: Mapped[str] = db.Column(db.Text, nullable=False)
    help: Mapped[str] = db.Column(db.Text, nullable=False)
    help_url: Mapped[str] = db.Column(db.String(255), nullable=True)
    # comma separated list of tags
    tags: Mapped[str] = db.Column(db.Text, nullable=False) 
    any: Mapped[List[Check]] = db.relationship('Check', secondary=RuleChecks, lazy='subquery', backref=db.backref('rules', lazy=True))
    all: Mapped[List[Check]] = db.relationship('Check', secondary=RuleChecksAll, lazy='subquery', backref=db.backref('rules_all', lazy=True))
    none: Mapped[List[Check]] = db.relationship('Check', secondary=RuleChecksNone, lazy='subquery', backref=db.backref('rules_none', lazy=True))
    impact: Mapped[impact_levels] = db.Column(db.String(10), nullable=False, default="minor")
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    json: Mapped[str] = db.Column(db.Text, nullable=True)  # Store the full rule as JSON for reference
    
    def __repr__(self):
        return f"<Rule {self.name} (id={self.id})>"
    
    def __init__(self, name, selector="*", exclude_hidden=True, enabled=True, matches=None, description="", help="", help_url=None, tags=[], impact='minor'):
        # Check if rule with same name exists
        check_rules = db.session.query(Rule).filter_by(name=name).first()
        if check_rules:
            raise ValueError("Rule with this name already exists")
        self.name = name
        self.selector = selector
        self.exclude_hidden = exclude_hidden
        self.enabled = enabled
        self.matches = matches
        self.description = description
        self.help = help
        self.help_url = help_url
        self.tags = ",".join(tags)
        self.impact = impact
        self.json = None  # will be set in save()

    def save(self):
        if not self.impact or self.impact not in ["minor", "moderate", "serious", "critical"]:
            raise ValueError("impact must be one of: minor, moderate, serious, critical")
        # expand tags into a comma separated list, replace spaces with underscores, escape special characters
        self.tags = ",".join(tag.strip().replace(" ", "_") for tag in self.tags.split(","))
        self.description = self.description.strip()
        self.help = self.help.strip()
        if self.help_url:
            if not is_valid_url(self.help_url):
                raise ValueError("help_url must be a valid URL")
            self.help_url = self.help_url.strip()

        self.enabled = bool(self.enabled)
        self.exclude_hidden = bool(self.exclude_hidden)
        
        # check this at the end because it can be expensive
        if self.matches:
            self.matches = self.matches.strip()
            
            # remove comments from matches
            self.matches = re.sub(r'/\*.*?\*/', '', self.matches, flags=re.DOTALL)  # remove /* */ comments
            self.matches = re.sub(r'//.*?$', '', self.matches, flags=re.MULTILINE)  # remove // comments
            self.matches = self.matches.strip()
            
            if not is_single_arrow_function(self.matches, ["node", "virtualNode?"]):
                raise ValueError("matches must be a valid JavaScript function starting with '(node, virtualNode?) => ' and be of type (node: Element, virtualNode?: any) => boolean")

        else:
            self.matches = None

        self.to_js_object(update=True)

        db.session.add(self)
        db.session.commit()
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "selector": self.selector,
            "exclude_hidden": self.exclude_hidden,
            "enabled": self.enabled,
            "matches": self.matches,
            "description": self.description,
            "help": self.help,
            "help_url": self.help_url,
            "tags": self.tags.split(","),
            "any": [check.id for check in self.any],
            "all": [check.id for check in self.all],
            "none": [check.id for check in self.none],
            "impact": self.impact,
            "created_at": self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": self.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    
    def from_json(self, data):
        
        self.name = data.get("name", self.name)
        self.selector = data.get("selector", self.selector)
        self.exclude_hidden = data.get("excludeHidden", self.exclude_hidden)
        self.enabled = data.get("enabled", self.enabled)
        self.matches = data.get("matches", self.matches)
        self.description = data.get("description", self.description)
        self.help = data.get("help", self.help)
        self.help_url = data.get("helpUrl", self.help_url)
        self.tags = ",".join(data.get("tags", self.tags.split(",")))
        self.impact = data.get("impact", self.impact)


        # Handle checks
        any_checks = data.get("any", [])
        all_checks = data.get("all", [])
        none_checks = data.get("none", [])

        def get_checks_by_dicts(check_dicts: List[dict]) -> List[Check]:
            result = []
            for check_data in check_dicts:
                check = db.session.query(Check).filter_by(name=check_data.get("name")).first()
                if check:
                    check.from_json(check_data)
                else:
                    check = Check(
                        name=check_data.get("name", ""),
                        evaluate=check_data.get("evaluate", ""),
                        options=json.dumps(check_data.get("options")) if check_data.get("options") is not None else None,
                        description=check_data.get("description", ""),
                        impact=check_data.get("impact", "minor"),
                        pass_text=check_data.get("pass_text", ""),
                        fail_text=check_data.get("fail_text", ""),
                        incomplete_text=check_data.get("incomplete_text", "")
                    )
                    check.validate()
                    
                result.append(check)
            return result

        self.any = get_checks_by_dicts(any_checks)
        self.all = get_checks_by_dicts(all_checks)
        self.none = get_checks_by_dicts(none_checks)

        
        return self
    
    
    def getChecksJson(self) -> List[dict]:
        """Get the full check details for the rule."""
        return [check.to_js_object() for check in self.any + self.all + self.none]
        
    
    def to_json(self, detailed: bool = False) -> dict:
        """Convert the Rule object to a JSON serializable format. 

        If detailed is True, it will include the full check details, otherwise just the names. for use in axe runner configuration.

        Returns:
            str: JSON string representation of the Rule.
        """
        json_rule = {
            "name": self.name,
            "selector": self.selector,
            "excludeHidden": self.exclude_hidden,
            "enabled": self.enabled,
            "matches": self.matches,
            "description": self.description,
            "help": self.help,
            "helpUrl": self.help_url,
            "tags": self.tags.split(","),
            "any": [check.to_json() if detailed else check.name for check in self.any],
            "all": [check.to_json() if detailed else check.name for check in self.all],
            "none": [check.to_json() if detailed else check.name for check in self.none],
            "impact": self.impact,
        }

        return json_rule
    
    
    @staticmethod
    def get_axe_config(rules: List['Rule']) -> str:
        """Generate the axe-core configuration JSON string from a list of Rule objects.

        Args:
            rules (List[Rule]): List of Rule objects to include in the configuration.

        Returns:
            str: JSON string representation of the axe-core configuration.
        """
        all_rules = []
        all_checks = set()
        for rule in rules:
            all_rules.append(rule.to_js_object())
            all_checks.update(rule.getChecksJson())
        
        # Generate the final configuration JSON string
        config = f"""{{ "checks": [{','.join(list(all_checks))}],"rules": [{','.join(list(all_rules))}]}}"""
        return config
    
    # for use in axe report
    def to_js_object(self, update = False, force = False) -> str:
        """
        Covert the Rule to a JavaScript object string for use in axe-core configuration. 
        If update is True, it will update the json field in the database. If force is True, it will commit the change immediately.
        """
        
        if not update:
            return self.json if self.json else self.to_js_object(update=True, force=True)
        
        js_object = f"""{{
                id: "{self.name}",
                selector: "{self.selector}",
                excludeHidden: {self.exclude_hidden and 'true' or 'false'},
                enabled: {self.enabled and 'true' or 'false'},
                matches: {self.matches},
                description: "{self.description}",
                help: "{self.help}",
                impact: "{self.impact}",
                helpUrl: "{self.help_url}",
                tags: [{",".join(f'"{tag}"' for tag in self.tags.split(","))}],
                any: [{",".join(f'"{check.name}"' for check in self.any)}],
                all: [{",".join(f'"{check.name}"' for check in self.all)}],
                none: [{",".join(f'"{check.name}"' for check in self.none)}],
                metadata: {{
                    description: "{self.description}",
                    help: "{self.help}",
                    helpUrl: "{self.help_url}",
                }},
            }}""" 
        
        is_valid = is_valid_object(js_object)
        
        if not is_valid:
            raise ValueError("Generated JavaScript object is not valid, please check the rule fields for invalid characters.")
        
        
        if update:
            self.json = js_object
            if force:
                db.session.add(self)
                db.session.commit()
        
        return js_object



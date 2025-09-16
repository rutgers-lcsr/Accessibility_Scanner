from flask import Blueprint, app, json, redirect, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, jwt_required, unset_jwt_cookies, set_access_cookies, set_refresh_cookies
from models import db
from authentication.login import admin_required
from utils.javascript import is_single_arrow_function, is_valid_js, is_valid_object
from models.rules import Check, Rule

axe_bp = Blueprint('axe', __name__)

@axe_bp.route("/validate_javascript/", methods=["POST"])
@admin_required
def validate_javascript():
    """Check if a string is valid JavaScript"""
    data = request.get_json()
    s = data.get('s')

    if s is None:
        return jsonify({'error': 'Missing parameter s'}), 400

    type_js = data.get('type', 'js')

    if type_js not in ['js', 'object', 'arrow_function', 'rule_match_function', 'check_eval_function']:
        return jsonify({'error': 'Invalid type, must be one of js, object, arrow_function, rule_match_function, check_eval_function'}), 400
    
    if type_js == 'js':
        valid = is_valid_js(s)
    elif type_js == 'object':
        valid = is_valid_object(s)
    elif type_js == 'arrow_function':
        valid = is_single_arrow_function(s, [])
    elif type_js == 'rule_match_function':
        valid = is_single_arrow_function(s, ["node", "virtualNode?"])
    elif type_js == 'check_eval_function':
        valid = is_single_arrow_function(s, ["node", "options?", "virtualNode?"], optional_async_function=True)

    return jsonify({'valid': valid}), 200

@axe_bp.route("/rules/tags/", methods=["GET"])
@admin_required
def get_rule_tags():
    tags = db.session.query(Rule.tags).distinct().all()
    # split comma-separated tags and flatten the list
    tags = [tag for sublist in [t[0].split(",") for t in tags if t[0]] for tag in sublist]
    # strip whitespace and remove empty tags
    tags = [tag.strip() for tag in tags if tag]
    # get unique tags
    tags = list(set(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"] + tags))
    tags.sort()

    return jsonify(tags), 200

@axe_bp.route("/rules/", methods=["GET"])
@admin_required
def list_rules():
    search = request.args.getlist('search')
    query = db.session.query(Rule)
    if search:
        for s in search:
            query = query.filter(Rule.tags.like(f"%{s}%"))

    rules = query.all()
    return jsonify([rule.to_dict() for rule in rules]), 200

@axe_bp.route("/rules/", methods=["POST"])
@admin_required
def create_rule():
    data = request.get_json()

    try:
        rule = Rule(
            name=data.get("name"),
            selector=data.get("selector", "*"),
            exclude_hidden=data.get("exclude_hidden", True),
            enabled=data.get("enabled", True),
            matches=data.get("matches"),
            description=data.get("description", ""),
            help=data.get("help", ""),
            help_url=data.get("help_url"),
            tags=data.get("tags", ""),
            impact=data.get("impact"),
        )
        
        
        rule.save()
        return jsonify(rule.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@axe_bp.route("/rules/<int:rule_id>/", methods=["GET"])
@admin_required
def get_rule(rule_id):
    rule = db.session.query(Rule).filter_by(id=rule_id).first()

    if not rule:
        return jsonify({'error': 'Rule not found'}), 404

    return jsonify(rule.to_dict()), 200

@axe_bp.route("/rules/<int:rule_id>/checks/", methods=["GET"])
@admin_required
def get_rule_checks(rule_id):
    rule = db.session.query(Rule).filter_by(id=rule_id).first()

    if not rule:
        return jsonify({'error': 'Rule not found'}), 404

    return jsonify({
        'any': [check.to_dict() for check in rule.any],
        'all': [check.to_dict() for check in rule.all],
        'none': [check.to_dict() for check in rule.none],
    }), 200

@axe_bp.route("/rules/import/", methods=["POST"])
@admin_required
def import_rule():
    data = request.get_json()
    try:
        rule = Rule.from_json(data)
        rule.save()
        return jsonify(rule.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@axe_bp.route("/rules/<int:rule_id>/export/", methods=["GET"])
@admin_required
def export_rule(rule_id):
    rule = db.session.query(Rule).filter_by(id=rule_id).first()

    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    
    return jsonify(rule.to_json()), 200

@axe_bp.route("/rules/<int:rule_id>/", methods=["PATCH"])
@admin_required
def update_rule(rule_id):
    data = request.get_json()
    rule = db.session.query(Rule).filter_by(id=rule_id).first()

    if not rule:
        return jsonify({'error': 'Rule not found'}), 404

    try:
        rule.selector = data.get("selector", rule.selector)
        rule.exclude_hidden = data.get("exclude_hidden", rule.exclude_hidden)
        rule.enabled = data.get("enabled", rule.enabled)
        rule.matches = data.get("matches", rule.matches)
        rule.description = data.get("description", rule.description)
        rule.help = data.get("help", rule.help)
        rule.help_url = data.get("help_url", rule.help_url)
        rule.tags = ",".join(data.get("tags", [tag.strip() for tag in rule.tags.split(",") if tag.strip()]))

        rule.impact = data.get("impact", rule.impact)
        
        # Update associated checks
        any_checks_ids = data.get("any", [check.id for check in rule.any])
        all_checks_ids = data.get("all", [check.id for check in rule.all])
        none_checks_ids = data.get("none", [check.id for check in rule.none])
        any_checks = db.session.query(Check).filter(Check.id.in_(any_checks_ids)).distinct().all()
        all_checks = db.session.query(Check).filter(Check.id.in_(all_checks_ids)).distinct().all()
        none_checks = db.session.query(Check).filter(Check.id.in_(none_checks_ids)).distinct().all()

    
        all_rule_checks_ids = [ check.id for check in rule.any + rule.all + rule.none]
        new_checks_ids = list(set(any_checks_ids + all_checks_ids + none_checks_ids))
        
        checks_to_delete = set(all_rule_checks_ids) - set(new_checks_ids)
        
        # delete checks that are no longer associated with the rule
        for check_id in checks_to_delete:
            check = db.session.query(Check).filter_by(id=check_id).first()
            if check:
                db.session.delete(check)

        rule.any = any_checks
        rule.all = all_checks
        rule.none = none_checks

        rule.save()
        return jsonify(rule.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@axe_bp.route("/rules/<int:rule_id>/", methods=["DELETE"])
@admin_required
def delete_rule(rule_id):
    rule = db.session.query(Rule).filter_by(id=rule_id).first()
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    try:

        # mark associated checks for deletion        
        for check in rule.any + rule.all + rule.none:
            db.session.delete(check)

        db.session.delete(rule)
        db.session.commit()
        return jsonify({'message': 'Rule deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    
@axe_bp.route("/checks/names/", methods=["GET"])
@admin_required
def get_check_names():
    checks = db.session.query(Check.id, Check.name).all()
    return jsonify([{'id': check.id, 'name': check.name} for check in checks]), 200


@axe_bp.route("/checks/", methods=["POST"])
@admin_required
def create_check():
    data = request.get_json()
    try:
        if not data.get("name") or not data.get("evaluate") or not data.get('pass_text') or not data.get('fail_text') :
            return jsonify({'error': 'Missing required fields: name, evaluate, pass_text, and fail_text'}), 400

        if not data.get("options"):
            data["options"] = ""
        
        
        check = Check(
            name=data.get("name"),
            evaluate=data.get("evaluate"),
            options=data.get("options", ""),
            pass_text=data.get("pass_text", ""),
            fail_text=data.get("fail_text", ""),
            incomplete_text=data.get("incomplete_text", ""),
        )
        
        
        check.save()

        return jsonify(check.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@axe_bp.route("/checks/<int:check_id>/", methods=["GET"])
@admin_required
def get_check(check_id):
    check = db.session.query(Check).filter_by(id=check_id).first()
    if not check:
        return jsonify({'error': 'Check not found'}), 404
    
    return jsonify(check.to_dict()), 200

@axe_bp.route("/checks/<int:check_id>/", methods=["PATCH"])
@admin_required
def update_check(check_id):
    data = request.get_json()
    check = db.session.query(Check).filter_by(id=check_id).first()

    if not check:
        return jsonify({'error': 'Check not found'}), 404

    try:
        check.name = data.get("name", check.name)
        check.evaluate = data.get("evaluate", check.evaluate)
        check.options = data.get("options", check.options)
        check.pass_text = data.get("pass_text", check.pass_text)
        check.fail_text = data.get("fail_text", check.fail_text)
        check.incomplete_text = data.get("incomplete_text", check.incomplete_text)

        check.save()
        return jsonify(check.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    
@axe_bp.route("/checks/<int:check_id>/", methods=["DELETE"])
@admin_required
def delete_check(check_id):
    check = db.session.query(Check).filter_by(id=check_id).first()
    if not check:
        return jsonify({'error': 'Check not found'}), 404

    try:
        db.session.delete(check)
        
        # Remove the check from any Rule relationships
        rules = db.session.query(Rule).filter(
            (Rule.any.any(id=check_id)) |
            (Rule.all.any(id=check_id)) |
            (Rule.none.any(id=check_id))
        ).all()
        for rule in rules:
            rule.any = [c for c in rule.any if c.id != check_id]
            rule.all = [c for c in rule.all if c.id != check_id]
            rule.none = [c for c in rule.none if c.id != check_id]
            rule.save()

        db.session.commit()

        return jsonify({'message': 'Check deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
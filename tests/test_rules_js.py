"""Tests for the JavaScript object strings generated for axe-core rule/check configuration.

The generated strings are evaluated inside the scanning browser via ``axe.configure``, so
every user-supplied field must be emitted as a proper JS literal: a stray quote must not be
able to add properties, and a rule without a ``matches`` function must not emit the Python
``None`` (a JS ``ReferenceError`` that used to break every scan using that rule).
"""
import esprima

from utils.javascript import is_valid_object


def _props(node):
    """Return {key: value-node} for an esprima ObjectExpression (quoted or bare keys)."""
    assert node.type == "ObjectExpression", node.type
    out = {}
    for prop in node.properties:
        key = prop.key.name if prop.key.type == "Identifier" else prop.key.value
        out[key] = prop.value
    return out


def _parse_object(js: str):
    program = esprima.parseScript(f"({js})")
    return _props(program.body[0].expression)


def _make_rule(name="custom-rule", **kwargs):
    from models.rules import Rule

    fields = dict(description="desc", help="help text", tags=["custom"], impact="minor")
    fields.update(kwargs)
    rule = Rule(name=name, **fields)
    rule.save()
    return rule


def test_rule_without_matches_omits_the_key(app):
    rule = _make_rule()
    js = rule.to_js_object()
    assert "None" not in js
    assert is_valid_object(js)
    assert "matches" not in _parse_object(js)


def test_rule_with_matches_emits_function(app):
    rule = _make_rule(matches="(node) => node.tagName === 'IMG'")
    props = _parse_object(rule.to_js_object())
    assert props["matches"].type == "ArrowFunctionExpression"


def test_rule_strings_are_escaped(app):
    description = 'say "hi" </script> back\\slash new\nline'
    rule = _make_rule(
        description=description,
        help='needs "quotes"',
        help_url="https://example.com/help?a=1&b=2",
    )
    props = _parse_object(rule.to_js_object())
    assert props["description"].value == description
    assert props["help"].value == 'needs "quotes"'
    assert props["helpUrl"].value == "https://example.com/help?a=1&b=2"
    metadata = {k: v.value for k, v in _props(props["metadata"]).items()}
    assert metadata == {
        "description": description,
        "help": 'needs "quotes"',
        "helpUrl": "https://example.com/help?a=1&b=2",
    }


def test_rule_metadata_cannot_inject_properties(app):
    # Crafted to close the string literal and smuggle in a new property.
    payload = 'a", evil: (() => 1)(), b: "c'
    rule = _make_rule(description=payload)
    props = _parse_object(rule.to_js_object())
    assert "evil" not in props
    assert props["description"].value == payload


def test_rule_without_help_url_omits_the_key(app):
    rule = _make_rule(help_url=None)
    props = _parse_object(rule.to_js_object())
    assert "helpUrl" not in props
    assert "helpUrl" not in _props(props["metadata"])


def test_rule_js_is_rebuilt_from_fields_not_cache(app):
    rule = _make_rule()
    rule.json = "{ matches: None }"  # a stale row written by the old generator
    assert "None" not in rule.to_js_object()


def test_check_strings_are_escaped(app):
    from models.rules import Check

    check = Check(
        name="my-check",
        evaluate="(node) => true",
        options='{"a": 1}',
        pass_text='all "good"',
        fail_text="bad",
        incomplete_text="",
    )
    check.save()
    props = _parse_object(check.to_js_object())
    assert props["id"].value == "my-check"
    assert props["evaluate"].type == "ArrowFunctionExpression"
    messages = _props(_props(props["metadata"])["messages"])
    assert messages["pass"].value == 'all "good"'
    assert messages["fail"].value == "bad"


def test_website_ace_config_is_valid_for_rule_without_matches(app, make_user, make_website):
    from models.rules import Check

    check = Check(name="img-has-alt", evaluate="(node) => !!node.alt", pass_text="ok", fail_text="no")
    check.save()
    rule = _make_rule(name="img-alt-custom", tags=["wcag2a"])
    rule.any = [check]
    rule.save()

    website = make_website(make_user())  # default tags include wcag2a
    config = website.get_ace_config()
    assert config
    assert is_valid_object(config)

    parsed = _parse_object(config)
    rules = parsed["rules"].elements
    assert len(rules) == 1
    rule_props = _props(rules[0])
    assert "matches" not in rule_props
    assert [e.value for e in rule_props["any"].elements] == ["img-has-alt"]
    assert [_props(c)["id"].value for c in parsed["checks"].elements] == ["img-has-alt"]


def _make_check(evaluate, name="my-check"):
    from models.rules import Check

    check = Check(name=name, evaluate=evaluate, pass_text="ok", fail_text="no")
    check.save()
    return check


def test_comments_are_removed_from_evaluate(app):
    check = _make_check("/* doc */ (node) => {\n  // why\n  return true; /* end */\n}")
    assert "/*" not in check.evaluate and "//" not in check.evaluate
    assert _parse_object(check.to_js_object())["evaluate"].type == "ArrowFunctionExpression"


def test_comment_markers_inside_literals_are_kept(app):
    # The old regex cut these at the // and rejected the check as invalid JavaScript.
    evaluate = "(node) => node.href.startsWith('https://') && `/*${node.id}*/` !== '' && !/\\/\\//.test(node.title)"
    check = _make_check(evaluate)
    assert check.evaluate == evaluate


def test_comment_markers_inside_matches_literals_are_kept(app):
    matches = "(node) => node.getAttribute('href') !== 'http://example.com' // external"
    rule = _make_rule(matches=matches)
    assert rule.matches == "(node) => node.getAttribute('href') !== 'http://example.com'"


def test_builtin_axe_rule_names_are_rejected(app):
    import pytest

    with pytest.raises(ValueError, match="built-in axe-core rule"):
        _make_rule(name="image-alt")


def test_builtin_axe_check_names_are_rejected(app):
    import pytest

    with pytest.raises(ValueError, match="built-in axe-core check"):
        _make_check("(node) => true", name="has-alt")


def test_axe_id_list_matches_the_bundled_axe():
    import json
    import re
    import shutil
    import subprocess

    import pytest

    from models.rules import AXE_IDS_PATH

    axe_path = AXE_IDS_PATH.with_name("axe.min.js")
    ids = json.loads(AXE_IDS_PATH.read_text())
    header = axe_path.read_text()[:100]
    assert re.search(r"axe v(\S+)", header).group(1) == ids["version"], (
        "axe.min.js was upgraded; regenerate axe_ids.json (command in models/rules.py)"
    )

    if not shutil.which("node"):
        pytest.skip("node is not installed")
    script = (
        "const axe=require(process.argv[1]);"
        "console.log(JSON.stringify({rules: axe.getRules().map(r=>r.ruleId).sort(),"
        " checks: Object.keys(axe._audit.checks).sort()}))"
    )
    out = subprocess.run(["node", "-e", script, str(axe_path)], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == {"rules": ids["rules"], "checks": ids["checks"]}

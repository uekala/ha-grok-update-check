from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT_PATH = ROOT / "blueprints" / "automation" / "grok_update_check.yaml"


class BlueprintLoader(yaml.SafeLoader):
    """Load Home Assistant's !input tags as ordinary reference objects."""


def _input_tag(loader, node):
    return {"__input__": loader.construct_scalar(node)}


BlueprintLoader.add_constructor("!input", _input_tag)


def _declared_inputs(section):
    """Collect input names, including Home Assistant's grouped input sections."""
    for key, value in section.items():
        if isinstance(value, dict) and "input" in value and "selector" not in value:
            yield from _declared_inputs(value["input"])
        else:
            yield key


def _used_inputs(node):
    if isinstance(node, dict):
        if "__input__" in node:
            yield node["__input__"]
            return
        for value in node.values():
            yield from _used_inputs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _used_inputs(value)


def _actions(node):
    if isinstance(node, dict):
        action = node.get("action")
        if isinstance(action, str):
            yield action
        for value in node.values():
            yield from _actions(value)
    elif isinstance(node, list):
        for value in node:
            yield from _actions(value)


def load_blueprint():
    assert BLUEPRINT_PATH.is_file(), f"Blueprint not found: {BLUEPRINT_PATH}"
    return yaml.load(BLUEPRINT_PATH.read_text(encoding="utf-8"), Loader=BlueprintLoader)


def test_blueprint_metadata_is_complete():
    data = load_blueprint()
    meta = data["blueprint"]

    assert meta["domain"] == "automation"
    assert meta["name"]
    assert meta["author"]
    assert meta["source_url"] == (
        "https://github.com/uekala/ha-grok-update-check/"
        "blob/main/blueprints/automation/grok_update_check.yaml"
    )
    assert meta["homeassistant"]["min_version"] == "2026.7.0"


def test_every_declared_input_is_used_and_every_used_input_is_declared():
    data = load_blueprint()
    declared = set(_declared_inputs(data["blueprint"]["input"]))
    body = {key: value for key, value in data.items() if key != "blueprint"}
    used = set(_used_inputs(body))

    assert declared, "No blueprint inputs were declared"
    assert used == declared, (
        f"Unused inputs: {sorted(declared - used)}; "
        f"undeclared inputs: {sorted(used - declared)}"
    )


def test_blueprint_checks_updates_and_calls_grok():
    data = load_blueprint()

    assert data["mode"] == "queued"
    assert data["triggers"], "No update trigger configured"
    assert data["triggers"][0]["entity_id"] == "!input update_entities" or (
        "update_entities" in set(_used_inputs(data["triggers"][0]))
    )
    actions = set(_actions(data["actions"]))
    assert "grok_conversation.ask" in actions
    assert "persistent_notification.create" in actions


def test_blueprint_has_a_manual_no_updates_message():
    data = load_blueprint()
    body = data["actions"]
    rendered = repr(body)
    assert "no_updates_text" in set(_used_inputs(body))
    assert "failure_text" in set(_used_inputs(body))
    assert "mobile_app" in rendered

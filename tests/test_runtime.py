"""Run the blueprint in a real Home Assistant test instance.

The blueprint is loaded with Home Assistant's own YAML loader and blueprint
code, the inputs are substituted, and the resulting automation runs against
real state changes and the real time-pattern trigger. Only two things are
replaced: the Grok service (a fake that records requests) and the phone
notification (a device action that needs a paired Companion app; it becomes a
recording service with the same title and message).
"""

from __future__ import annotations

import copy
from datetime import timedelta
from pathlib import Path

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.components import persistent_notification
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.yaml import load_yaml
from pytest_homeassistant_custom_component.common import async_fire_time_changed

BLUEPRINT_PATH = (
    Path(__file__).resolve().parents[1]
    / "blueprints"
    / "automation"
    / "grok_update_check.yaml"
)
CORE = "update.home_assistant_core_update"
OS = "update.home_assistant_operating_system_update"
MEMORY = "input_text.grok_update_check"
START = dt_util.parse_datetime("2026-11-10T08:02:00+00:00")


def _phone_notifications_to_service(node):
    """Replace mobile_app device actions with a recording service call."""
    if isinstance(node, list):
        return [_phone_notifications_to_service(item) for item in node]
    if isinstance(node, dict):
        if node.get("domain") == "mobile_app" and node.get("type") == "notify":
            data = {"title": node["title"], "message": node["message"]}
            if "data" in node:
                data["data"] = node["data"]
            return {"action": "test.phone", "data": data}
        return {
            key: _phone_notifications_to_service(value) for key, value in node.items()
        }
    return node


def automation_config(**inputs) -> dict:
    blueprint = Blueprint(
        load_yaml(BLUEPRINT_PATH),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )
    values = {
        "update_entities": [CORE, OS],
        "grok_entry": "grok_entry_id",
        "notify_device": "phone_device_id",
        **inputs,
    }
    bp_inputs = BlueprintInputs(
        blueprint,
        {"use_blueprint": {"path": "uekala/grok_update_check.yaml", "input": values}},
    )
    bp_inputs.validate()
    config = copy.deepcopy(bp_inputs.async_substitute())
    config["id"] = "grok_update_check"
    config["alias"] = "Update check with Grok"
    return _phone_notifications_to_service(config)


class Recorder:
    def __init__(self) -> None:
        self.grok: list[dict] = []
        self.phone: list[dict] = []
        self.fail_grok = False


@pytest.fixture
async def recorder(hass: HomeAssistant) -> Recorder:
    rec = Recorder()

    async def grok_ask(call: ServiceCall) -> dict:
        rec.grok.append(dict(call.data))
        if rec.fail_grok:
            raise HomeAssistantError("xAI not reachable")
        return {
            "response_text": "Recommendation: Install\n- nothing reported\nSources: x"
        }

    async def phone(call: ServiceCall) -> None:
        rec.phone.append(dict(call.data))

    hass.services.async_register(
        "grok_conversation", "ask", grok_ask, supports_response=SupportsResponse.ONLY
    )
    hass.services.async_register("test", "phone", phone)
    assert await async_setup_component(hass, "persistent_notification", {})
    return rec


async def setup(hass: HomeAssistant, freezer, **inputs) -> None:
    freezer.move_to(START)
    # Updates exist and are up to date before anything happens, as in a real system.
    set_update(hass, CORE, "off", latest="2026.11.0")
    set_update(hass, OS, "off", latest="17.0")
    assert await async_setup_component(
        hass, "automation", {"automation": [automation_config(**inputs)]}
    )
    await hass.async_block_till_done()


def set_update(
    hass: HomeAssistant, entity_id: str, state: str, latest: str = "2026.11.1"
) -> None:
    hass.states.async_set(
        entity_id,
        state,
        {
            "title": "Home Assistant Core"
            if entity_id == CORE
            else "Home Assistant Operating System",
            "installed_version": "2026.11.0",
            "latest_version": latest,
            "release_url": "https://example.invalid/release",
        },
    )


async def advance(hass: HomeAssistant, freezer, delta: timedelta) -> None:
    """Move time forward and fire every quarter-hour tick on the way, like HA does."""
    end = dt_util.utcnow() + delta
    while True:
        now = dt_util.utcnow()
        tick = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
        tick += timedelta(minutes=15)
        target = min(tick, end)
        if target <= now:
            break
        freezer.move_to(target)
        async_fire_time_changed(hass, target)
        await hass.async_block_till_done()
        if target == end:
            break


async def restart_like(
    hass: HomeAssistant, entity_id: str, latest: str = "2026.11.1"
) -> None:
    """After a restart, update entities come back and their last_changed is reset."""
    hass.states.async_set(entity_id, "unavailable")
    await hass.async_block_till_done()
    set_update(hass, entity_id, "on", latest)
    await hass.async_block_till_done()


async def test_checks_once_after_the_wait(hass, freezer, recorder) -> None:
    await setup(hass, freezer, delay_hours=4)
    set_update(hass, CORE, "on")
    await hass.async_block_till_done()

    await advance(hass, freezer, timedelta(hours=3, minutes=50))
    assert recorder.grok == []

    await advance(hass, freezer, timedelta(minutes=30))
    assert len(recorder.grok) == 1
    assert "Installed version: 2026.11.0" in recorder.grok[0]["input_data"]
    assert "New version: 2026.11.1" in recorder.grok[0]["input_data"]
    assert recorder.phone[0]["title"] == "Update: Home Assistant Core 2026.11.1"
    assert recorder.phone[0]["message"].startswith("Recommendation: Install")
    assert "Sources" not in recorder.phone[0]["message"]
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    saved = notifications["grok_update_check_update_home_assistant_core_update"]
    assert saved["title"] == "Update check: Home Assistant Core 2026.11.0 → 2026.11.1"
    assert "Sources: x" in saved["message"]

    await advance(hass, freezer, timedelta(hours=6))
    assert len(recorder.grok) == 1, "an update must be checked only once"


async def test_update_installed_during_the_wait_is_not_checked(
    hass, freezer, recorder
) -> None:
    await setup(hass, freezer, delay_hours=4)
    set_update(hass, CORE, "on")
    await advance(hass, freezer, timedelta(hours=2))
    set_update(hass, CORE, "off")
    await advance(hass, freezer, timedelta(hours=4))
    assert recorder.grok == []


async def test_restart_during_the_wait_no_longer_skips_the_check(
    hass, freezer, recorder
) -> None:
    await setup(hass, freezer, delay_hours=4)
    set_update(hass, CORE, "on")
    await advance(hass, freezer, timedelta(hours=2))

    await restart_like(hass, CORE)
    await advance(hass, freezer, timedelta(hours=3, minutes=50))
    assert recorder.grok == [], "the wait starts again after the restart"
    await advance(hass, freezer, timedelta(minutes=30))
    assert len(recorder.grok) == 1


async def test_without_memory_a_restart_checks_a_pending_update_once_more(
    hass, freezer, recorder
) -> None:
    await setup(hass, freezer, delay_hours=1)
    set_update(hass, CORE, "on")
    await advance(hass, freezer, timedelta(hours=2))
    assert len(recorder.grok) == 1

    await restart_like(hass, CORE)
    await advance(hass, freezer, timedelta(hours=3))
    assert len(recorder.grok) == 2


async def test_memory_prevents_repeat_checks_and_catches_newer_versions(
    hass, freezer, recorder
) -> None:
    assert await async_setup_component(
        hass, "input_text", {"input_text": {"grok_update_check": {"max": 255}}}
    )
    await setup(hass, freezer, delay_hours=1, memory=MEMORY)
    set_update(hass, CORE, "on")
    set_update(hass, OS, "on", latest="17.1")
    await advance(hass, freezer, timedelta(hours=2))
    assert len(recorder.grok) == 2
    assert hass.states.get(MEMORY).state == "0=2026.11.1;1=17.1"

    await restart_like(hass, CORE)
    await restart_like(hass, OS, latest="17.1")
    await advance(hass, freezer, timedelta(hours=3))
    assert len(recorder.grok) == 2, "remembered versions are not checked again"

    # A newer version replaces the pending one without the state changing.
    set_update(hass, CORE, "on", latest="2026.11.2")
    await advance(hass, freezer, timedelta(minutes=15))
    assert len(recorder.grok) == 3
    assert "New version: 2026.11.2" in recorder.grok[2]["input_data"]
    assert hass.states.get(MEMORY).state == "0=2026.11.2;1=17.1"

    # Installed updates drop out of the memory.
    set_update(hass, OS, "off", latest="17.1")
    set_update(hass, CORE, "on", latest="2026.11.3")
    await advance(hass, freezer, timedelta(minutes=15))
    assert hass.states.get(MEMORY).state == "0=2026.11.3"


async def test_memory_respects_the_helper_length(hass, freezer, recorder) -> None:
    assert await async_setup_component(
        hass, "input_text", {"input_text": {"grok_update_check": {"max": 12}}}
    )
    await setup(hass, freezer, delay_hours=0, memory=MEMORY)
    set_update(hass, CORE, "on")
    set_update(hass, OS, "on", latest="17.1")
    await advance(hass, freezer, timedelta(hours=2))
    # The second entry does not fit; that update is still checked only once.
    assert len(recorder.grok) == 2
    assert hass.states.get(MEMORY).state == "0=2026.11.1"


async def test_memory_keeps_the_wait_for_a_new_update_after_an_install(
    hass, freezer, recorder
) -> None:
    assert await async_setup_component(
        hass, "input_text", {"input_text": {"grok_update_check": {"max": 255}}}
    )
    await setup(hass, freezer, delay_hours=4, memory=MEMORY)
    set_update(hass, CORE, "on")
    await advance(hass, freezer, timedelta(hours=5))
    assert len(recorder.grok) == 1

    # Installed; no run in between, so the memory still holds the old version.
    set_update(hass, CORE, "off")
    await advance(hass, freezer, timedelta(hours=1))
    set_update(hass, CORE, "on", latest="2026.12.0")
    await advance(hass, freezer, timedelta(hours=3, minutes=45))
    assert len(recorder.grok) == 1, "a new update still waits the configured time"
    await advance(hass, freezer, timedelta(minutes=30))
    assert len(recorder.grok) == 2


async def test_manual_run_checks_every_pending_update_right_away(
    hass, freezer, recorder
) -> None:
    await setup(hass, freezer, delay_hours=4)
    set_update(hass, CORE, "on")
    set_update(hass, OS, "off")
    await hass.async_block_till_done()

    await hass.services.async_call(
        "automation",
        "trigger",
        {"entity_id": "automation.update_check_with_grok"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert len(recorder.grok) == 1
    assert recorder.phone[0]["title"] == "Update: Home Assistant Core 2026.11.1"


async def test_manual_run_without_pending_updates_says_so(
    hass, freezer, recorder
) -> None:
    await setup(hass, freezer, delay_hours=4)
    set_update(hass, CORE, "off")
    await hass.services.async_call(
        "automation",
        "trigger",
        {"entity_id": "automation.update_check_with_grok"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert recorder.grok == []
    assert recorder.phone == [
        {
            "title": "Update check",
            "message": "No pending updates among the watched entities.",
        }
    ]


async def test_failed_grok_request_sends_the_failure_text(
    hass, freezer, recorder
) -> None:
    recorder.fail_grok = True
    await setup(hass, freezer, delay_hours=0)
    set_update(hass, CORE, "on")
    await advance(hass, freezer, timedelta(minutes=15))
    assert len(recorder.grok) == 1
    assert (
        recorder.phone[0]["message"]
        == "Grok check failed. Please read the release notes yourself."
    )


async def test_idle_ticks_do_not_run_the_actions(hass, freezer, recorder) -> None:
    await setup(hass, freezer, delay_hours=4)
    set_update(hass, CORE, "off")
    await advance(hass, freezer, timedelta(hours=2))
    assert recorder.phone == []
    state = hass.states.get("automation.update_check_with_grok")
    assert state.attributes.get("last_triggered") is None

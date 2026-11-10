"""Use Home Assistant's test harness when it is installed (requirements_test.txt).

The structural tests in test_blueprint.py only need PyYAML; the runtime tests in
test_runtime.py run the blueprint in a real test instance of Home Assistant and
are skipped without the harness.
"""

try:
    import pytest_homeassistant_custom_component  # noqa: F401
except ImportError:  # pragma: no cover - lightweight validation job
    pass
else:
    pytest_plugins = ["pytest_homeassistant_custom_component"]

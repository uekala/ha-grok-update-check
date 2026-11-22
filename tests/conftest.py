"""Nutzt die Testumgebung von Home Assistant, wenn sie installiert ist (requirements_test.txt).

Die Aufbautests in test_blueprint.py brauchen nur PyYAML; die Laufzeittests in
test_runtime.py führen den Blueprint in einer echten Testinstanz von Home
Assistant aus und werden ohne diese Umgebung übersprungen.
"""

try:
    import pytest_homeassistant_custom_component  # noqa: F401
except ImportError:  # pragma: no cover - lightweight validation job
    pass
else:
    pytest_plugins = ["pytest_homeassistant_custom_component"]

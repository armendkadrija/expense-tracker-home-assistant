"""Validates services.yaml against Home Assistant's REAL service-
description schema.

This is the second boundary-crossing test from the final review: the
`image` selector doesn't exist in Home Assistant, but HA's real loader
(`homeassistant.helpers.service._load_services_file`) swallows an invalid
services.yaml silently (catches `vol.Invalid`, logs a warning, and treats
the file as if it had no descriptions) instead of raising. That silent
failure is exactly why a broken services.yaml shipped undetected. This
test applies the same schema HA's real loader applies, directly, so a
regression here fails loudly in CI instead of quietly in production.
"""
import os

from homeassistant.helpers.service import _SERVICES_SCHEMA
from homeassistant.util.yaml import load_yaml_dict

SERVICES_YAML_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "custom_components",
    "expense_tracker",
    "services.yaml",
)


def test_services_yaml_validates_against_real_service_schema():
    raw = load_yaml_dict(SERVICES_YAML_PATH)

    _SERVICES_SCHEMA(raw)

"""Privacy-denylist tests.

These tests protect the v4.5 §11A.5 promise that observation events carry metadata only.
If one of them starts failing, do not relax the assertion — fix the payload.
"""

from __future__ import annotations

import pytest

from src.privacy import CONTENT_FIELD_DENYLIST, PrivacyViolation, strip_and_validate


@pytest.mark.parametrize("banned_key", sorted(CONTENT_FIELD_DENYLIST))
def test_denylist_rejects_each_banned_key_at_top_level(banned_key: str) -> None:
    with pytest.raises(PrivacyViolation):
        strip_and_validate({banned_key: "anything"})


def test_denylist_rejects_banned_key_nested() -> None:
    with pytest.raises(PrivacyViolation):
        strip_and_validate({"metadata": {"extra": {"keystrokes": "hello"}}})


def test_denylist_rejects_banned_key_in_list() -> None:
    with pytest.raises(PrivacyViolation):
        strip_and_validate({"events": [{"clipboard_content": "x"}]})


def test_denylist_is_case_insensitive() -> None:
    with pytest.raises(PrivacyViolation):
        strip_and_validate({"Keystrokes": "x"})


def test_metadata_with_only_structure_passes() -> None:
    # Field NAMES are permitted (e.g. a form has a field called "email");
    # field VALUES are not. This shape is the allowed one.
    strip_and_validate(
        {
            "action_type": "form_submission_event",
            "target_application": "servicenow",
            "metadata": {"form_fields_present": ["email", "department", "ticket_id"]},
        }
    )

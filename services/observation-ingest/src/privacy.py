"""Privacy-by-design validator for observation events.

The Watch layer captures *patterns*, not *content*. This module is the last line of defence
before events leave the ingest boundary — any payload that contains a banned key is rejected.

The denylist is deliberately conservative. Adding a new key here is fine. Removing one requires
a works-council conversation (v4.5 §11A.5) and a DPIA amendment.
"""

from __future__ import annotations

# Banned leaf keys anywhere in the event payload. Matched by key name, case-insensitive.
CONTENT_FIELD_DENYLIST: frozenset[str] = frozenset(
    {
        # Raw user input
        "keystrokes",
        "keystroke_buffer",
        "typed_text",
        "input_value",
        "input_values",
        # Clipboard
        "clipboard",
        "clipboard_content",
        "clipboard_text",
        # Form content (field NAMES are OK; field VALUES are not)
        "form_value",
        "form_values",
        "field_value",
        "field_values",
        # Screen / image
        "screenshot",
        "screen_content",
        "image_bytes",
        "pixel_data",
        # Files
        "file_contents",
        "file_bytes",
        # URL query secrets (URLs themselves are allowed under the domain allowlist;
        # query strings are stripped before they hit ingest but we still defence-in-depth).
        "url_query_params",
        "query_params_raw",
        # Auth leakage
        "access_token",
        "id_token",
        "refresh_token",
        "cookie",
        "cookies",
        "session_cookie",
    }
)


class PrivacyViolation(ValueError):
    """Raised when an event contains a banned content field."""


def strip_and_validate(payload: object, *, path: str = "$") -> None:
    """Walk the payload tree; raise PrivacyViolation on any banned key.

    This is a read-only check — it does not mutate the payload. Ingest only forwards events that
    pass this walk.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and key.lower() in CONTENT_FIELD_DENYLIST:
                raise PrivacyViolation(f"disallowed content field at {path}.{key}")
            strip_and_validate(value, path=f"{path}.{key}")
    elif isinstance(payload, list):
        for idx, value in enumerate(payload):
            strip_and_validate(value, path=f"{path}[{idx}]")
    # Scalars are fine — we only ban by key, not by value-shape.

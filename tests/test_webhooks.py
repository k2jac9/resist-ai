"""Tests for the webhook notification helpers.

Regression: format_slack_message previously injected a literal ``None`` into
the Slack ``blocks`` list when the payload was empty. Slack rejects messages
containing a null block, so delivery would fail.
"""
from src.sdk.webhooks import format_slack_message


def _all_blocks(message):
    blocks = []
    for attachment in message["attachments"]:
        blocks.extend(attachment["blocks"])
    return blocks


def test_empty_payload_has_no_none_block():
    msg = format_slack_message("pipeline.completed", {})
    blocks = _all_blocks(msg)
    assert None not in blocks
    # Only the header block should remain.
    assert [b["type"] for b in blocks] == ["header"]


def test_payload_renders_fields_section():
    msg = format_slack_message("pipeline.completed", {"target": "NDM-1", "hits": 3})
    blocks = _all_blocks(msg)
    assert None not in blocks
    section = next(b for b in blocks if b["type"] == "section")
    assert len(section["fields"]) == 2


def test_color_reflects_event():
    completed = format_slack_message("pipeline.completed", {})
    failed = format_slack_message("pipeline.failed", {})
    assert completed["attachments"][0]["color"] == "#2eb886"
    assert failed["attachments"][0]["color"] == "#dc3545"

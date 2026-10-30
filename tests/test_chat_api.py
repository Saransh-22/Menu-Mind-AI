"""
Integration tests for the AI Chat Assistant, Conversations, and Menu Design API endpoints.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_conversation_lifecycle():
    # 1. Create a conversation
    resp = client.post(
        "/api/chat/conversations",
        json={"restaurant_id": 4, "run_id": 6, "title": "Test Integration Chat"},
    )
    assert resp.status_code == 201
    data = resp.json()
    conv_id = data["id"]
    assert conv_id.startswith("conv_")
    assert data["title"] == "Test Integration Chat"

    # 2. List conversations
    list_resp = client.get(f"/api/chat/conversations?restaurant_id=4")
    assert list_resp.status_code == 200
    conv_ids = [c["id"] for c in list_resp.json()]
    assert conv_id in conv_ids

    # 3. Update title
    patch_resp = client.patch(
        f"/api/chat/conversations/{conv_id}",
        json={"title": "Updated Integration Chat"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated Integration Chat"

    # 4. Send a message
    msg_resp = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"content": "What is our best-selling dish?", "run_id": 6},
    )
    assert msg_resp.status_code == 200
    turn = msg_resp.json()
    assert "user_message" in turn
    assert "assistant_message" in turn
    assert "agent_response" in turn
    assert turn["assistant_message"]["role"] == "assistant"
    assert len(turn["assistant_message"]["content"]) > 0

    # 5. List messages
    msgs_resp = client.get(f"/api/chat/conversations/{conv_id}/messages")
    assert msgs_resp.status_code == 200
    msgs = msgs_resp.json()
    assert len(msgs) >= 2

    # 6. Generate Menu Design endpoint
    menu_draft_payload = {
        "title": "Weekend Chef Specials",
        "concept": "Traditional Punjabi Signature Dishes",
        "currency": "₹",
        "categories": [
            {
                "category": "Specials",
                "items": [
                    {
                        "name": "Paneer Tikka Special",
                        "category": "Specials",
                        "price": 280.0,
                        "description": "Clay oven grilled cottage cheese.",
                    }
                ],
            }
        ],
        "total_items": 1,
    }
    design_resp = client.post(
        f"/api/chat/conversations/{conv_id}/menu-designs",
        json={"menu_draft": menu_draft_payload, "spec": {"style": "Traditional Indian"}},
    )
    assert design_resp.status_code == 201
    design = design_resp.json()
    assert design["title"] == "Weekend Chef Specials"
    assert "Paneer Tikka Special" in design["html_preview"]

    # 7. Delete conversation
    del_resp = client.delete(f"/api/chat/conversations/{conv_id}")
    assert del_resp.status_code == 204

    # Verify 404 after deletion
    get_del = client.get(f"/api/chat/conversations/{conv_id}")
    assert get_del.status_code == 404

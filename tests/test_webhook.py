import base64
import hashlib
import hmac
import json

from app import create_app

SECRET = "test-channel-secret"


def signed(body):
    digest = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def text_event(text, user="U123", token="reply-token-1"):
    return {
        "destination": "Uxxxxxxxx",
        "events": [{
            "type": "message", "mode": "active", "timestamp": 1700000000000,
            "webhookEventId": "01H000000000000000000000000", "deliveryContext": {"isRedelivery": False},
            "source": {"type": "user", "userId": user}, "replyToken": token,
            "message": {"id": "1", "type": "text", "quoteToken": "q", "text": text},
        }],
    }


def client_and_sent():
    sent = []
    app = create_app(SECRET, lambda token, texts: sent.append((token, texts)))
    return app.test_client(), sent


def post(client, payload, signature=None):
    body = json.dumps(payload, ensure_ascii=False)
    return client.post("/callback", data=body.encode(), content_type="application/json",
                       headers={"X-Line-Signature": signature if signature is not None else signed(body)})


def test_a_signed_text_message_gets_a_reply():
    client, sent = client_and_sent()
    response = post(client, text_event("營業時間"))
    assert response.status_code == 200
    assert sent == [("reply-token-1", ["營業時間：每天 08:00–18:00"])]


def test_a_bad_signature_is_rejected_without_a_reply():
    client, sent = client_and_sent()
    response = post(client, text_event("菜單"), signature="not-a-valid-signature")
    assert response.status_code == 400
    assert sent == []


def test_the_cart_follows_the_line_user():
    client, sent = client_and_sent()
    post(client, text_event("點 拿鐵 2", user="U1", token="t1"))
    post(client, text_event("購物車", user="U2", token="t2"))
    post(client, text_event("購物車", user="U1", token="t3"))
    assert sent[1] == ("t2", ["購物車是空的"])
    assert sent[2] == ("t3", ["購物車：拿鐵 × 2，合計 NT$220"])


def test_non_text_events_are_accepted_and_ignored():
    client, sent = client_and_sent()
    payload = {"destination": "Uxxxxxxxx", "events": [{
        "type": "follow", "mode": "active", "timestamp": 1700000000000,
        "webhookEventId": "01H000000000000000000000001", "deliveryContext": {"isRedelivery": False},
        "source": {"type": "user", "userId": "U9"}, "replyToken": "t9", "follow": {"isUnblocked": False}}]}
    assert post(client, payload).status_code == 200
    assert sent == []


def test_health_check():
    client, _ = client_and_sent()
    assert client.get("/healthz").data == b"ok"

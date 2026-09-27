import os

from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from bot.replies import Orders, reply_for


def line_sender(access_token):
    from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, ReplyMessageRequest, TextMessage

    configuration = Configuration(access_token=access_token)

    def send(reply_token, texts):
        with ApiClient(configuration) as client:
            MessagingApi(client).reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=t) for t in texts]))

    return send


def create_app(channel_secret, send):
    app = Flask(__name__)
    handler = WebhookHandler(channel_secret)
    orders = Orders()

    @handler.add(MessageEvent, message=TextMessageContent)
    def on_text(event):
        user_id = getattr(event.source, "user_id", None) or "anonymous"
        send(event.reply_token, reply_for(event.message.text, user_id, orders))

    @app.post("/callback")
    def callback():
        signature = request.headers.get("X-Line-Signature", "")
        try:
            handler.handle(request.get_data(as_text=True), signature)
        except InvalidSignatureError:
            abort(400)
        return "OK"

    @app.get("/healthz")
    def healthz():
        return "ok"

    return app


if __name__ == "__main__":
    application = create_app(os.environ["LINE_CHANNEL_SECRET"],
                             line_sender(os.environ["LINE_CHANNEL_ACCESS_TOKEN"]))
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))

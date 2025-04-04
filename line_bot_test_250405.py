from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

line_bot_api = LineBotApi('uCHR0VdxUl3iyr0YAifLoGQHcdvMxGEEuk8ubMywuP7luPTgJJxAxpjecf0RKiv9zYMVtALaQlYzXU7JqYjfJEs/iRtuHqt2e68O6ELSJLV8LEQH4l4W99oiVRy7XZXF4YTxg0iiO6fIj0P4F7YMgwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('8fa23de32b81a5680eedd89d8f10249c')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    reply = f"你說的是：{msg}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run()

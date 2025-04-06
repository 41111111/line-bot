import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 從環境變數取得 Line Bot 的 Secret 和 Token
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)

# LINE Webhook 接收路徑
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        events = parser.parse(body, signature)  # 解析收到的事件
    except InvalidSignatureError:
        abort(400)  # 驗證不通過
    # 處理每一個事件
    for event in events:
        # 如果是訊息事件且是文字訊息
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
            reply_text = f"你說了{event.message.text}"
            # 回覆訊息給用戶
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
    return 'OK'

if __name__ == "__main__":
    app.run()

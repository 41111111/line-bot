import face_recognition
import cv2
import pickle
import os
import requests
from PIL import Image
from io import BytesIO
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__, static_url_path='/static')

def fetch_frame_from_mjpeg(url, save_as='esp32.jpg'):
    print("🔄 嘗試從 MJPEG 串流擷取畫面...")
    stream = requests.get(url, stream=True)
    bytes_data = b''

    for chunk in stream.iter_content(chunk_size=1024):
        bytes_data += chunk
        a = bytes_data.find(b'\xff\xd8')  # JPEG 開始
        b = bytes_data.find(b'\xff\xd9')  # JPEG 結尾

        if a != -1 and b != -1:
            jpg_data = bytes_data[a:b+2]
            img = Image.open(BytesIO(jpg_data))
            img.save(img.save("static/esp32.jpg"))
            print(f"✅ 已儲存圖片到 {save_as}")
            break

    stream.close()
    return save_as
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    
    if msg == "你好":
        # 擷取圖片
        image_path = fetch_frame_from_mjpeg("http://172.20.10.11:81/stream")
        
        if image_path and os.path.exists(image_path):
            # 傳圖片
            from linebot.models import ImageSendMessage
            image_message = ImageSendMessage(
                original_content_url='https://你的域名.onrender.com/static/esp32.jpg',
                preview_image_url='https://你的域名.onrender.com/static/esp32.jpg'
            )
            line_bot_api.reply_message(event.reply_token, image_message)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 擷取失敗，請稍後再試"))

    else:
        reply = f"你說了：{msg}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

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

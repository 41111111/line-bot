import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import requests
from PIL import Image
from io import BytesIO

app = Flask(__name__, static_url_path='/static')

# 用環境變數存 LINE 機器人的密鑰
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

ESP32_URL = "https://f3a5-2001-b400-e4de-b8e-d50c-39cc-6723-1e97.ngrok-free.app/stream"  # 替換成你的 ESP32 實際 IP

def fetch_frame_from_mjpeg(url, save_as='static/esp32.jpg'):
    print("🔄 擷取 ESP32 影像...")
    try:
        stream = requests.get(url, stream=True, timeout=10)
        bytes_data = b''

        for chunk in stream.iter_content(chunk_size=1024):
            bytes_data += chunk
            a = bytes_data.find(b'\xff\xd8')
            b = bytes_data.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg_data = bytes_data[a:b+2]
                img = Image.open(BytesIO(jpg_data))
                img.save(save_as)
                print(f"✅ 已儲存圖片到 {save_as}")
                break

        stream.close()
        return save_as
    except Exception as e:
        print(f"❌ 擷取失敗：{e}")
        return None

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()

    if msg == "你好":
        image_path = fetch_frame_from_mjpeg(ESP32_URL)
        if image_path and os.path.exists(image_path):
            domain = os.getenv("RENDER_EXTERNAL_HOSTNAME", "你的網址.onrender.com")
            image_url = f"https://{domain}/static/esp32.jpg"
            image_message = ImageSendMessage(
                original_content_url=image_url,
                preview_image_url=image_url
            )
            line_bot_api.reply_message(event.reply_token, image_message)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 擷取圖片失敗"))
    else:
        reply = f"你說了：{msg}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run()

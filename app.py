import os
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
from linebot.exceptions import InvalidSignatureError
from PIL import Image
from io import BytesIO
import time
import cv2
import numpy as np

app = Flask(__name__, static_url_path='/static')

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

ESP32_URL = "https://dcba-2001-b400-e486-791e-9979-5dc4-c584-d4d.ngrok-free.app/stream"

def fetch_frame_from_mjpeg(url, save_as='static/esp32.jpg', min_bytes=10000):
    print("🔄 擷取 ESP32 影像...")
    try:
        os.makedirs("static", exist_ok=True)
        stream = requests.get(url, stream=True, timeout=10)
        bytes_data = b''
        start_time = time.time()

        for chunk in stream.iter_content(chunk_size=1024):
            bytes_data += chunk
            a = bytes_data.find(b'\xff\xd8')
            b = bytes_data.find(b'\xff\xd9')

            if a != -1 and b != -1:
                jpg_data = bytes_data[a:b+2]
                if len(jpg_data) < min_bytes and time.time() - start_time < 3:
                    continue
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
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    print(f"\U0001f464 LINE 使用者說：{msg}")

    if msg == "畫面":
        image_path = fetch_frame_from_mjpeg(ESP32_URL)
        if image_path and os.path.exists(image_path):
            domain = os.getenv("RENDER_EXTERNAL_HOSTNAME", "你的網址.onrender.com")
            timestamp = int(time.time())
            image_url = f"https://{domain}/static/esp32.jpg?t={timestamp}"

            image_message = ImageSendMessage(
                original_content_url=image_url,
                preview_image_url=image_url
            )
            line_bot_api.reply_message(event.reply_token, image_message)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 擷取圖片失敗"))

    elif msg == "人臉辨識":
        image_path = fetch_frame_from_mjpeg(ESP32_URL)
        if image_path and os.path.exists(image_path):
            domain = os.getenv("RENDER_EXTERNAL_HOSTNAME", "你的網址.onrender.com")
            timestamp = int(time.time())
            image_url = f"https://{domain}/static/esp32.jpg?t={timestamp}"

            with open(image_path, 'rb') as img:
                files = {'image': img}
                try:
                    res = requests.post("https://rekognition.onrender.com/recognize", files=files, timeout=10)
                    result = res.json()
                    name = result.get("result", "辨識失敗")
                    sim = result.get("similarity", 0)
                    reply = f"✅ 辨識結果：{name}\n相似度：{sim:.2f}%" if sim else name
                except Exception as e:
                    reply = f"❌ 錯誤：{e}"

            image_message = ImageSendMessage(
                original_content_url=image_url,
                preview_image_url=image_url
            )
            text_message = TextSendMessage(text=reply)
            line_bot_api.reply_message(event.reply_token, [image_message, text_message])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 無法擷取圖片"))

elif msg == "光學辨識":
    image_path = fetch_frame_from_mjpeg(ESP32_URL)
    if image_path and os.path.exists(image_path):
        domain = os.getenv("RENDER_EXTERNAL_HOSTNAME", "你的網址.onrender.com")
        timestamp = int(time.time())
        image_url = f"https://{domain}/static/esp32.jpg?t={timestamp}"

        try:
            with open(image_path, 'rb') as f:
                res = requests.post(
                    'https://api.ocr.space/parse/image',
                    files={'file': f},
                    data={
                        'apikey': 'K89122706188957',
                        'language': 'chi_tra',
                        'isOverlayRequired': False,
                        'OCREngine': 2,
                        'scale': False,
                        'filetype': 'JPG'
                    },
                    timeout=10
                )

            if res.status_code == 200:
                result = res.json()
                if "ParsedResults" in result and result["ParsedResults"]:
                    text = result["ParsedResults"][0]["ParsedText"].strip()
                    if not text:
                        text = "❌ 無法辨識（結果為空）"
                else:
                    text = f"❌ 無法辨識（ParsedResults 不存在）\n回傳內容：{result}"
            else:
                text = f"❌ API 回傳錯誤碼 {res.status_code}\n回應內容：{res.text}"

        except requests.exceptions.RequestException as e:
            text = f"❌ 請求錯誤：{str(e)}"
        except Exception as e:
            text = f"❌ 例外錯誤：{str(e)}"

        image_message = ImageSendMessage(
            original_content_url=image_url,
            preview_image_url=image_url
        )
        text_message = TextSendMessage(text=text)
        line_bot_api.reply_message(event.reply_token, [image_message, text_message])
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 擷取圖片失敗"))


    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 不在指令範圍內"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

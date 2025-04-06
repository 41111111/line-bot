import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
from linebot.exceptions import InvalidSignatureError
import paho.mqtt.client as mqtt
import requests
from PIL import Image
from io import BytesIO

app = Flask(__name__, static_url_path='/static')

# ===== LINE Bot 設定 =====
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# ===== MQTT 設定 =====
MQTT_BROKER = "broker.emqx.io"  # 或 localhost
MQTT_PORT = 1883
MQTT_TOPIC_SUB = "chatbotjohnisluckbot"
MQTT_TOPIC_PUB = "chatbotjohnisluckuser"
user_token = None  # 用來記錄目前使用者 LINE ID

# ===== ESP32 串流設定 =====
ESP32_URL = " https://f3a5-2001-b400-e4de-b8e-d50c-39cc-6723-1e97.ngrok-free.app/stream"  # 改成 ngrok 給你的公開網址

# 擷取 ESP32 畫面函式
def fetch_frame_from_mjpeg(url, save_as='static/esp32.jpg'):
    print("🔄 擷取 ESP32 影像...")
    try:
        os.makedirs("static", exist_ok=True)
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

# ===== MQTT 回呼設定 =====
def on_connect(client, userdata, flags, rc):
    print("🔗 已連線 MQTT")
    client.subscribe(MQTT_TOPIC_SUB)

def on_message(client, userdata, msg):
    global user_token
    response = msg.payload.decode()

    if user_token:
        print(f"🤖 MQTT 回覆給 LINE 使用者：{response}")
        line_bot_api.push_message(user_token, TextSendMessage(text=response))

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ===== LINE Webhook 接收區 =====
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ===== 處理 LINE 使用者訊息 =====
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global user_token
    msg = event.message.text.strip()
    user_token = event.source.user_id

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
        print(f"👤 LINE 使用者說：{msg}")
        mqtt_client.publish(MQTT_TOPIC_PUB, 'john_line')
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⏳ 指令已送出，等待回覆..."))
        result = mqtt_client.publish(MQTT_TOPIC_PUB, msg)
        print(f"📤 MQTT 發送結果：{result.rc}（0 表示成功）")

if __name__ == "__main__":
    app.run()

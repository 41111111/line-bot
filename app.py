import os
import threading
import time
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
connected_event = threading.Event()
mqtt_client = mqtt.Client()
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
    if rc == 0:
        print("🔗 MQTT 已連線成功")
        client.subscribe(MQTT_TOPIC_SUB)
        print(f"📥 已訂閱主題：{MQTT_TOPIC_SUB}")
    else:
        print(f"❌ MQTT 連線失敗，錯誤碼：{rc}")

def on_message(client, userdata, msg):
    message = msg.payload.decode()
    print(f"📥 MQTT 收到：{msg.topic} -> {message}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT , 60)
#特別重要 要用forever才能保住心跳
def mqtt_loop_thread():
    mqtt_client.loop_forever()   
threading.Thread(target=mqtt_loop_thread, daemon=True).start()
def mqtt_loop_connect():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT , 60)
threading.Thread(target=mqtt_loop_connect, daemon=True).start()

if connected_event.wait(timeout=5):
    print("✅ MQTT 連線完成，繼續啟動 Flask")
else:
    print("⚠️ 連線逾時，請檢查 broker 設定")

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

    print(f"👤 LINE 使用者說：{msg}")

    # ====== 指令：畫面 ======
    if msg == "畫面":
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

    # ====== 指令：人臉辨識 ======
    elif msg == "人臉辨識":
        mqtt_msg = "john_1"
        result = mqtt_client.publish(MQTT_TOPIC_PUB, mqtt_msg)
        print(f"📤 MQTT 發送：{mqtt_msg}，rc = {result.rc}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已發送：人臉辨識 指令"))

    # ====== 指令：光學辨識 ======
    elif msg == "光學辨識":
        mqtt_msg = "john_2"
        result = mqtt_client.publish(MQTT_TOPIC_PUB, mqtt_msg)
        print(f"📤 MQTT 發送：{mqtt_msg}，rc = {result.rc}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已發送：光學辨識 指令"))

    # ====== 其他：非指令內容 ======
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 不在指令範圍內"))
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render 會提供環境變數 PORT
    app.run(host="0.0.0.0", port=port)

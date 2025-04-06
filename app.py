import os
import paho.mqtt.client as mqtt
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import requests
from PIL import Image
from io import BytesIO

# Flask 應用初始化
app = Flask(__name__, static_url_path='/static')

# 用環境變數存 LINE 機器人的密鑰# LINE Bot 初始化
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 儲存使用者 token（用來回 MQTT 訊息時知道要回誰）
user_token = None

#ESP32 實際 IP
ESP32_URL = "https://f3a5-2001-b400-e4de-b8e-d50c-39cc-6723-1e97.ngrok-free.app/stream"  

# MQTT 設定
MQTT_BROKER = "broker.hivemq.com"  # 你也可以用本地 localhost
MQTT_PORT = 1883
MQTT_TOPIC_SUB = "chatbot/bot"
MQTT_TOPIC_PUB = "chatbot/user"

# MQTT 回呼：連線成功
def on_connect(client, userdata, flags, rc):
    print("🔗 已連接 MQTT")
    client.subscribe(MQTT_TOPIC_SUB)

# MQTT 回呼：收到來自 MQTT 的訊息 → 回傳給 LINE
def on_message(client, userdata, msg):
    global user_token
    response = msg.payload.decode()

    # 回傳給 LINE 使用者
    if user_token:
        print(f"🔁 從 MQTT 收到訊息，發送給 LINE：{response}")
        line_bot_api.push_message(user_token, TextSendMessage(text=response))

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

# 初始化 MQTT 客戶端
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()  # 注意用 loop_start()，非 loop_forever()，避免阻塞 Flask

# LINE Webhook 接收器
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# LINE 訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global user_token
    msg = event.message.text.strip()
    user_token = event.source.user_id  # 儲存發話者 ID，用來推播回 MQTT 訊息

    print(f"👤 LINE 使用者說：{msg}")
    mqtt_client.publish(MQTT_TOPIC_PUB, msg)  # 發送到 MQTT
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⏳ 正在處理你的訊息..."))

# 啟動 Flask
if __name__ == "__main__":
    app.run()

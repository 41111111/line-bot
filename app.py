import os
import paho.mqtt.client as mqtt
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# ===== LINE Bot 設定 =====
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# ===== MQTT 設定 =====
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "chatbotjohnisluckuser"

mqtt_client = mqtt.Client(transport="websockets")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("🔗 MQTT 已連線成功")
    else:
        print("❌ MQTT 連線失敗，錯誤碼：", rc)

mqtt_client.on_connect = on_connect
mqtt_client.connect("broker.emqx.io", 8083, 60)
mqtt_client.loop_start()  # ✅ 背景執行，讓 Flask 可正常啟動

# ===== Webhook 路由 =====
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ===== 處理文字訊息事件 =====
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.strip()
    print(f"👤 LINE 使用者說：{user_msg}")

    # ✅ 發送到 MQTT topic
    result = mqtt_client.publish(MQTT_TOPIC, user_msg)
    print(f"📤 MQTT 發送結果 rc={result.rc}，內容：{user_msg}")

    # ✅ 回覆 LINE 使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="✅ 訊息已送出至 MQTT")
    )

# ===== Flask 啟動點 =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

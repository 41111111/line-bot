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

mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("🔗 MQTT 已連線成功")
    else:
        print("❌ MQTT 連線失敗，錯誤碼：", rc)
        
def on_message(client, userdata, msg):
    print(f"📥 收到訊息：{msg.topic} -> {msg.payload.decode()}")
    
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT , 60)
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
    global user_token
    user_token = event.source.user_id
    msg = event.message.text.strip()

    print(f"👤 LINE 使用者說：{msg}")
    
    # ✅ 檢查 MQTT client 是否還連著
    if not mqtt_client.is_connected():
        print("⚠️ MQTT client 尚未連線！請確認 broker 有正常啟動")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⚠️ MQTT 尚未連線，請稍後再試")
        )
        return

    # ✅ 發送 MQTT，記錄詳細結果
    info = mqtt_client.publish(MQTT_TOPIC_PUB, msg)
    print(f"📤 嘗試發送 MQTT：topic = {MQTT_TOPIC_PUB}, payload = {msg}")
    
    # 確認訊息有成功送出（等一下 delivery 完成）
    result = info.wait_for_publish(timeout=3)
    print(f"📬 publish() 結果：rc = {info.rc}, wait result = {result}")

    if info.rc == 0 and result:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="✅ 指令已送出至 MQTT")
        )
    else:
        print("❌ MQTT 發送可能失敗，訊息未送達")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="❌ 發送 MQTT 失敗，請稍後重試")
        )
# ===== Flask 啟動點 =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

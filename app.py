import os
import threading
import paho.mqtt.client as mqtt
import time
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)
connected_event = threading.Event()
# ===== LINE Bot 設定 =====
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# ===== MQTT 設定 =====
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC_PUB = "chatbotjohnisluckuser"

mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("🔗 MQTT 已連線成功")
        connected_event.set()  # ✅ 設定成功旗標
    else:
        print(f"❌ MQTT 連線失敗，錯誤碼：{rc}")
        
def on_message(client, userdata, msg):
    print(f"📥 收到訊息：{msg.topic} -> {msg.payload.decode()}")
    
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT , 60)
"""
mqtt_client.loop_start()  # ✅ 背景執行，讓 Flask 可正常啟動
if connected_event.wait(timeout=5):
    print("✅ MQTT 連線完成，繼續啟動 Flask")
else:
    print("⚠️ MQTT 連線逾時，請檢查 broker 設定")
"""
def mqtt_loop_thread():
    mqtt_client.loop_forever()
threading.Thread(target=mqtt_loop_thread, daemon=True).start()
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
    msg = event.message.text.strip()
    user_token = event.source.user_id

    print(f"👤 LINE 使用者說：{msg}")

    # ✅ 先馬上回覆 LINE（不管 MQTT 發成功與否）
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="✅ 指令已送出至 MQTT")
        )
    except Exception as e:
        print(f"⚠️ 回覆 LINE 失敗：{e}")

    # ✅ 再發 MQTT（背景處理）
    try:
        if not mqtt_client.is_connected():
            print("🔁 MQTT 重新連線中...")
            mqtt_client.reconnect()
            time.sleep(1)
        print(f"🔍 MQTT 狀態：已連線 = {mqtt_client.is_connected()}")
        info = mqtt_client.publish(MQTT_TOPIC_PUB, msg, retain=True, qos=1)
        info.wait_for_publish(timeout=5)
    
        if info.is_published():
            print("📬 MQTT 發送成功")
        else:
            print("❌ MQTT 發送失敗（未完成 publish）")
    except Exception as e:
        print(f"🚨 MQTT 發送出錯：{e}")



        
# ===== Flask 啟動點 =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

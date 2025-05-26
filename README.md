# 專案架構圖

```mermaid
graph TD
    User[使用者手機（LINE 聊天室）]
    LINE[LINE Bot（Render）]
    ESP32[ESP32-CAM + HW-416]
    Ngrok[Ngrok 串流轉發]
    Rekognition[Render - 人臉辨識 API]
    OCR[OCR.Space 光學辨識 API]
    MQTT[EMQX Broker]

    ESP32 -->|影像串流| Ngrok
    User -->|傳送指令：「畫面 / 人臉辨識 / 光學辨識」| LINE
    LINE -->|擷取畫面| Ngrok
    LINE -->|擷取畫面後分析| Rekognition
    LINE -->|擷取畫面後分析| OCR
    LINE -->|分析結果回傳| User

    ESP32 -->|紅外觸發| MQTT
    MQTT -->|MQTT 訊息通知| LINE
    LINE -->|警示推播| User


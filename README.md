# 專案架構圖

```mermaid
graph TD
    User[使用者手機]
    LINE[LINE Bot（Render）]
    ESP32[ESP32-CAM + HW-416]
    Ngrok[Ngrok 轉發串流]
    Rekognition[Render - 人臉辨識 API]
    OCR[OCR.Space 光學辨識 API]
    MQTT[EMQX Broker]
    
    User -->|傳送訊息| LINE
    LINE -->|發送「畫面」指令| Ngrok
    Ngrok -->|取得串流截圖| ESP32

    LINE -->|發送「人臉辨識」圖片| Rekognition
    LINE -->|發送「光學辨識」圖片| OCR

    ESP32 -->|紅外觸發| MQTT
    MQTT -->|MQTT 訊息通知| LINE

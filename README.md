```mermaid
graph TD
    User[5 使用者手機（LINE 聊天室）]
    LINE_Bot_Server[6 LINE Bot Server端]
    subgraph Render_Server [4 Render Server]
        LB[4_1 Line Bot Code]
        FR[4_2 人臉識別 Code]
        MS[4_3 Mqtt 監聽 Code]
        OCR[OCR API]
    end
    MQTT[3 EMQX Broker Mqtt server]
    ESP32[2 ESP32-CAM]
    HW416[1 HW-416紅外線感測器]
    Ngrok[7 Ngrok 串流轉發]
    OCR[OCR API]
    %% 使用者互動流程
    User <-->|傳送指令| LINE_Bot_Server
    LINE_Bot_Server <-->|LINE通訊協議| LB
    LB -->|擷取畫面| Ngrok
    LB <-->|辨識人臉| FR
    LB <-->|辨識LED| OCR
    
    %% 紅外線感測流程
    HW416 -->|紅外觸發| ESP32
    ESP32 -->|發送 MQTT 訊息| MQTT
    MQTT -->|推播 MQTT 訊息| MS
    MS -->|收到警示推播| LINE_Bot_Server
    
    %% 影像串流
    ESP32 -->|影像串流| Ngrok

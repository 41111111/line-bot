```mermaid
graph LR
    User[1 使用者手機（LINE 聊天室）]
    LINE_Bot_Server[2 LINE Bot Server端]
    subgraph Render_Server [3 Render Server]
        LB[3_1 Line Bot Code]
        FR[3_2 人臉識別 Code]
        MS[3_3 Mqtt 監聽 Code]
    end
    MQTT[4 EMQX Broker Mqtt server]
    ESP32[5 ESP32-CAM]
    HW416[6 HW-416紅外線感測器]
    Ngrok[7 Ngrok 串流轉發]

    %% 使用者互動流程
    User <-->|傳送指令| LINE_Bot_Server
    LINE_Bot_Server <-->|LINE通訊協議| LB
    LB -->|擷取畫面| Ngrok
    LB <-->|辨識人臉| FR
    LB <-->|辨識LED| OCR[OCR.Space OCR API]
    
    %% 紅外線感測流程
    HW416 -->|紅外觸發| ESP32
    ESP32 -->|發送 MQTT 訊息| MQTT
    MQTT -->|推播 MQTT 訊息| MS
    MS -->|收到警示推播| LINE_Bot_Server
    
    %% 影像串流
    ESP32 -->|影像串流| Ngrok

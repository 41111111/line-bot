```mermaid
graph LR
    User[使用者手機（LINE 聊天室）]

    subgraph Render_Server [Render Server]
        LB[Line Bot Code]
        FR[人臉識別 Code]
        MS[mqtt 監聽 Code]
    end
    LINE_Bot_Server[LINE Bot Server端]
    MQTT[EMQX Broker]
    ESP32[ESP32-CAM]
    HW416[HW-416\n紅外線感測器]
    Ngrok[Ngrok 串流轉發]

    %% 使用者互動流程
    User <-->|傳送指令| LINE_Bot_Server
    LINE_Bot_Server <-->| | LB
    LB -->|擷取畫面| Ngrok
    LB -->|擷取後送辨識| FR
    LB -->|擷取後送辨識| OCR[OCR.Space OCR API]
    FR -->|回傳分析結果| LB
    OCR -->|回傳文字辨識結果| LB
    

    %% 紅外線感測流程
    HW416 -->|紅外觸發| ESP32
    ESP32 -->|發送 MQTT 訊息| MQTT
    MS -->|訂閱 MQTT 訊息| MQTT
    MS -->|收到警示推播| LINE_Bot_Server
    

    %% 影像串流
    ESP32 -->|影像串流| Ngrok

graph TD
    User[使用者手機 (LINE)]
    LineBot[LINE Bot Server端]
    FaceRecog[人臉識別 Code (Render)]
    MQTTListen[MQTT 監聽 Code (Render)]
    MQTTServer[MQTT Server (EMQX Broker)]
    ESP32[ESP32-CAM]
    HW416[HW-416 紅外線感測器]
    Ngrok[Ngrok 串流轉發]
    OCR[OCR.Space OCR API]

    User -->|傳送指令：「畫面 / 人臉 / 光學」| LineBot
    LineBot -->|擷取畫面| Ngrok
    LineBot -->|擷取後送辨識| FaceRecog
    LineBot -->|擷取後送辨識| OCR
    FaceRecog -->|回傳分析結果| LineBot
    OCR -->|回傳文字辨識結果| LineBot
    LineBot -->|回傳結果| User

    HW416 -->|紅外觸發| ESP32
    ESP32 -->|發送 MQTT 訊息| MQTTServer
    MQTTListen -->|訂閱 MQTT 訊息| MQTTServer
    MQTTListen -->|收到警示推播| LineBot
    LineBot -->|警示訊息回傳| User

    ESP32 -->|影像串流| Ngrok

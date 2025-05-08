from flask import Flask, request, jsonify
import boto3
import os

app = Flask(__name__)

# 初始化 AWS Rekognition 用戶端
rekognition = boto3.client(
    'rekognition',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="ap-northeast-1"
)

COLLECTION_ID = "my-face-db"

@app.route("/recognize", methods=["POST"])
def recognize():
    if 'image' not in request.files:
        return jsonify({"error": "請上傳圖片 image 檔案欄位"}), 400

    image_file = request.files['image']
    image_bytes = image_file.read()

    try:
        response = rekognition.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=80
        )

        matches = response['FaceMatches']
        if matches:
            matched = matches[0]
            name = matched['Face']['ExternalImageId']
            similarity = matched['Similarity']
            return jsonify({"result": name, "similarity": similarity})
        else:
            return jsonify({"result": "未找到相符人臉"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return "✅ Rekognition API 正常運作，請 POST /recognize 上傳圖片"

if __name__ == '__main__':
    app.run(debug=True)

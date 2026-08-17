# app.py
from flask import Flask, request, render_template_string, redirect, url_for, jsonify
from PIL import Image
import io, os, json, traceback
import numpy as np
import tensorflow as tf
import requests
from datetime import datetime

# ---------------- CONFIG ----------------
ESP32_IP    = "http://192.168.1.103"      # <-- set to ESP32 IP printed in serial monitor
FLASK_PORT  = 5000
MODEL_PATH  = "plant_disease_model.h5"
LABELS_PATH = "class_label.json"          # {"Apple___Apple_scab": 0, ...}

STATIC_DIR  = "static"
LATEST_IMG  = os.path.join(STATIC_DIR, "latest.jpg")
os.makedirs(STATIC_DIR, exist_ok=True)

app = Flask(__name__)

# ---------------- MODEL LOAD ----------------
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    print(f"✅ Model loaded: {MODEL_PATH}")
    print("   Model input shape:", model.input_shape)  # (None, H, W, 3)
    _, in_h, in_w, _ = model.input_shape
    INPUT_SIZE = (int(in_w), int(in_h))               # PIL expects (W, H)
except Exception as e:
    print("❌ Failed to load model:", e)
    raise

# ---------------- LABELS LOAD ----------------
with open(LABELS_PATH, "r") as f:
    label_map = json.load(f)  # label -> index
INDEX_TO_LABEL = {int(v): k for k, v in label_map.items()}
print(f"✅ Loaded {len(INDEX_TO_LABEL)} class labels")

# keep the latest result
latest_result = {"prediction": "None", "confidence": 0.0, "at": "-"}

# ---------------- HELPERS ----------------
def predict_bytes(img_bytes: bytes):
    """Return (label, confidence_percent) from raw JPEG bytes."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = img.resize(INPUT_SIZE)                     # (W, H)
    arr = np.array(img).astype(np.float32) / 255.0
    arr = np.expand_dims(arr, axis=0)               # (1, H, W, 3)
    preds = model.predict(arr)[0]
    idx = int(np.argmax(preds))
    label = INDEX_TO_LABEL.get(idx, f"class_{idx}")
    conf = float(np.max(preds)) * 100.0
    return label, round(conf, 2)

def stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------- ROUTES ----------------
@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "esp32_ip": ESP32_IP,
        "model": MODEL_PATH,
        "labels": LABELS_PATH
    }), 200

@app.route("/")
def home():
    return render_template_string("""
<!doctype html>
<html>
  <head>
    <title>🌱 Plant Disease Detection</title>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
  </head>
  <body style="font-family: Arial; padding: 20px; max-width: 900px; margin:auto;">
    <h2>Plant Disease Detection</h2>
    <form action="{{ url_for('capture') }}" method="post">
      <button type="submit" style="padding:10px 16px;">📸 Capture Image</button>
    </form>
    <hr>
    <h3>Latest Result</h3>
    <p><strong>Disease:</strong> {{ pred }}</p>
    <p><strong>Confidence:</strong> {{ conf }}%</p>
    <p><small>Time: {{ at }}</small></p>
    <img src="{{ url_for('static', filename='latest.jpg') }}?t={{ ts }}" alt="latest" style="max-width: 360px; border:1px solid #ccc">
    <hr>
    <details>
      <summary>Debug Info</summary>
      <pre>ESP32_IP = {{ esp32 }}</pre>
    </details>
  </body>
</html>
    """,
    pred=latest_result["prediction"],
    conf=latest_result["confidence"],
    at=latest_result["at"],
    ts=int(datetime.now().timestamp()),
    esp32=ESP32_IP)

@app.route("/capture", methods=["POST"])
def capture():
    """
    Flask -> ESP32: GET /capture to make ESP32 take a photo and POST it back to /upload.
    """
    try:
        # small reachability check to your own server (optional but handy)
        try:
            rping = requests.get(f"http://127.0.0.1:{FLASK_PORT}/ping", timeout=3)
            print("Self /ping:", rping.status_code)
        except Exception as _:
            pass

        print(f"[capture] -> GET {ESP32_IP}/capture")
        r = requests.get(f"{ESP32_IP}/capture", timeout=20)
        print("[capture] <-", r.status_code, r.headers.get("content-type"))

        if r.status_code == 200 and "application/json" in r.headers.get("content-type",""):
            data = r.json()
            if "prediction" in data and "confidence" in data:
                latest_result.update({
                    "prediction": data["prediction"],
                    "confidence": data["confidence"],
                    "at": stamp()
                })
        elif r.status_code != 200:
            latest_result.update({
                "prediction": "ESP32 Error",
                "confidence": 0.0,
                "at": stamp()
            })
    except Exception as e:
        print("[capture] ERROR:", e)
        latest_result.update({
            "prediction": "ESP32 Trigger Failed",
            "confidence": f"{type(e).__name__}: {e}",
            "at": stamp()
        })
    return redirect(url_for("home"))

@app.route("/upload", methods=["POST"])
def upload():
    """
    ESP32 posts raw JPEG here (Content-Type: image/jpeg).
    Save, run inference, return JSON.
    """
    try:
        img_bytes = request.data
        if not img_bytes:
            return jsonify({"status":"error","error":"no image data"}), 400

        with open(LATEST_IMG, "wb") as f:
            f.write(img_bytes)

        label, conf = predict_bytes(img_bytes)
        latest_result.update({"prediction": label, "confidence": conf, "at": stamp()})

        return jsonify({"status":"success", "prediction": label, "confidence": conf}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status":"error","error": str(e)}), 500

# --------------- MAIN ----------------
if __name__ == "__main__":
    # IMPORTANT: 0.0.0.0 so ESP32 & phone can reach it over Wi-Fi
    app.run(host="0.0.0.0", port=5000, debug=True)
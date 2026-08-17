# app.py  – FINAL VERSION WITH FERTILIZER RECOMMENDATION + PRETTY UI

from flask import Flask, request, render_template, redirect, url_for, jsonify
from PIL import Image
import io
import os
import json
import traceback
from datetime import datetime

import numpy as np
import tensorflow as tf
import requests

# ---------------- CONFIG ----------------

# ❗ Change this to the IP that the ESP32 prints in the serial monitor
ESP32_IP = "http://10.143.57.92"

FLASK_PORT  = 5000
MODEL_PATH  = "plant_disease_model.h5"
LABELS_PATH = "class_label.json"      # {"Apple___Apple_scab": 0, ...}
DISEASE_INFO_PATH = "disease_info.json"   # fertilizer & description info

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
    label_map = json.load(f)  # label -> index (e.g. {"Apple___Apple_scab": 0, ...})

INDEX_TO_LABEL = {int(v): k for k, v in label_map.items()}
print(f"✅ Loaded {len(INDEX_TO_LABEL)} class labels")

# ---------------- DISEASE / FERTILIZER INFO LOAD ----------------
# Expected format (recommended):
# {
#   "Apple___Apple_scab": {
#       "description": "Fungal disease affecting apple leaves...",
#       "fertilizer": "Use balanced NPK 10-10-10 + copper-based fungicide ..."
#   },
#   "Tomato___healthy": {
#       "description": "No visible disease symptoms.",
#       "fertilizer": "Maintain regular NPK schedule, avoid overwatering."
#   }
# }
try:
    if os.path.exists(DISEASE_INFO_PATH):
        with open(DISEASE_INFO_PATH, "r") as f:
            DISEASE_INFO = json.load(f)
        print(f"✅ Loaded disease info for {len(DISEASE_INFO)} classes")
    else:
        print("⚠️ disease_info.json not found, using generic messages.")
        DISEASE_INFO = {}
except Exception as e:
    print("⚠️ Failed to load disease_info.json:", e)
    DISEASE_INFO = {}

# Generic fallback messages
GENERIC_HEALTHY_TEXT = (
    "The leaf appears healthy. Maintain good agronomic practices such as "
    "balanced NPK fertilization, regular irrigation, and periodic monitoring "
    "for early infection signs."
)
GENERIC_DISEASE_TEXT = (
    "The plant is likely affected by a disease. Remove heavily infected leaves "
    "and avoid overhead irrigation. Apply a recommended fungicide or bactericide "
    "as per local agricultural guidelines and use a balanced fertilizer to support recovery."
)

# ---------------- STATE ----------------
latest_result = {
    "prediction": "None",
    "confidence": 0.0,
    "at": "-",
    "fertilizer": "",
    "description": ""
}

# ---------------- HELPERS ----------------
def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_disease_info(label: str):
    """
    Return (description, fertilizer) text for a predicted label.
    Tries disease_info.json first, then falls back to generic text.
    """
    info = DISEASE_INFO.get(label)

    # If disease_info.json stores a simple string, treat it as fertilizer text
    if isinstance(info, str):
        desc = ""
        fert = info
    elif isinstance(info, dict):
        desc = info.get("description", "")
        fert = info.get("fertilizer", "")
    else:
        desc = ""
        fert = ""

    # Fallbacks if not present
    lower_label = label.lower()
    if not desc:
        if "healthy" in lower_label:
            desc = GENERIC_HEALTHY_TEXT
        else:
            desc = GENERIC_DISEASE_TEXT

    if not fert:
        if "healthy" in lower_label:
            fert = (
                "Apply a balanced NPK fertilizer (e.g., 10-10-10) at recommended dose, "
                "monitor soil moisture, and avoid over-fertilization."
            )
        else:
            fert = (
                "Use a disease-specific treatment as per local guidelines and support the "
                "plant with organic manure or balanced NPK to improve resistance."
            )

    return desc, fert


def predict_from_bytes(img_bytes: bytes):
    """
    Run model inference from raw JPEG bytes and return:
    (label, confidence_percent, description, fertilizer_text)
    """
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = img.resize(INPUT_SIZE)                     # (W, H)
    arr = np.array(img).astype(np.float32) / 255.0
    arr = np.expand_dims(arr, axis=0)               # (1, H, W, 3)

    preds = model.predict(arr)[0]
    idx = int(np.argmax(preds))
    label = INDEX_TO_LABEL.get(idx, f"class_{idx}")
    conf = float(np.max(preds)) * 100.0

    desc, fert = get_disease_info(label)
    return label, round(conf, 2), desc, fert


# ---------------- ROUTES ----------------

@app.route("/ping")
def ping():
    """Simple health check: returns 'pong'."""
    return "pong", 200


@app.route("/health")
def health():
    """JSON health info for debugging."""
    return jsonify({
        "status": "ok",
        "esp32_ip": ESP32_IP,
        "model": MODEL_PATH,
        "labels": LABELS_PATH,
        "disease_info_loaded": bool(DISEASE_INFO)
    }), 200


@app.route("/")
def home():
    """
    Main UI page – rendered using templates/index.html (pretty dashboard).
    """
    return render_template(
        "index.html",
        pred=latest_result["prediction"],
        conf=latest_result["confidence"],
        at=latest_result["at"],
        ts=int(datetime.now().timestamp()),
        esp32=ESP32_IP,
        latest_result=latest_result
    )


@app.route("/capture", methods=["POST"])
def capture():
    """
    Triggered when user clicks 'Capture Image' on the web page.
    Flask sends GET /capture to ESP32.
    ESP32 captures photo and POSTs JPEG to /upload.
    """
    try:
        print(f"[capture] -> GET {ESP32_IP}/capture")
        r = requests.get(f"{ESP32_IP}/capture", timeout=25)
        print("[capture] <-", r.status_code, r.headers.get("content-type"))

        if r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
            # If ESP32 directly returns prediction JSON (optional design)
            data = r.json()
            if "prediction" in data and "confidence" in data:
                desc, fert = get_disease_info(data["prediction"])
                latest_result.update({
                    "prediction": data["prediction"],
                    "confidence": float(data["confidence"]),
                    "at": now_stamp(),
                    "description": desc,
                    "fertilizer": fert
                })
        elif r.status_code != 200:
            latest_result.update({
                "prediction": "ESP32 Error",
                "confidence": 0.0,
                "at": now_stamp(),
                "description": "The ESP32 did not respond correctly to the capture request.",
                "fertilizer": ""
            })

    except Exception as e:
        print("[capture] ERROR:", e)
        latest_result.update({
            "prediction": "ESP32 Trigger Failed",
            "confidence": 0.0,
            "at": now_stamp(),
            "description": f"Flask could not contact the ESP32. Error: {type(e).__name__}: {e}",
            "fertilizer": ""
        })

    # Always return to main UI
    return redirect(url_for("home"))


@app.route("/upload", methods=["POST"])
def upload():
    """
    Endpoint for the ESP32-CAM.
    ESP32 sends raw JPEG bytes (Content-Type: image/jpeg).
    We save the image, run inference, and return JSON result.
    """
    try:
        img_bytes = request.data
        if not img_bytes:
            return jsonify({"status": "error", "error": "no image data"}), 400

        # Save image so it appears on the web UI
        with open(LATEST_IMG, "wb") as f:
            f.write(img_bytes)

        label, conf, desc, fert = predict_from_bytes(img_bytes)

        latest_result.update({
            "prediction": label,
            "confidence": conf,
            "at": now_stamp(),
            "description": desc,
            "fertilizer": fert
        })

        print(f"[upload] Pred: {label} ({conf:.2f}%)")

        return jsonify({
            "status": "success",
            "prediction": label,
            "confidence": conf,
            "description": desc,
            "fertilizer": fert
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500


# --------------- MAIN ----------------
if __name__ == "__main__":
    # 0.0.0.0 so ESP32 + phone can reach Flask over Wi-Fi
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=True)
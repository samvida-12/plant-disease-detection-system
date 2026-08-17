import serial
import numpy as np
import cv2
import tensorflow as tf
from io import BytesIO
from PIL import Image

# Load your trained model
model = tf.keras.models.load_model('plant_disease_model.h5')

# Open serial port
ser = serial.Serial('COM12', 115200, timeout=10)  # Replace COMx with your port (e.g., COM5)

print("Waiting for image from ESP32...")

while True:
    if ser.in_waiting:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        if line == "START":
            print("Receiving image...")
            image_bytes = bytearray()
            while True:
                if ser.in_waiting:
                    byte = ser.read()
                    image_bytes += byte
                    if image_bytes[-4:] == b'DONE':
                        image_bytes = image_bytes[:-4]  # remove "DONE"
                        break

            # Convert to image
            image_array = np.asarray(bytearray(image_bytes), dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if img is not None:
                # Optional: Save image
                cv2.imwrite("received.jpg", img)

                # Resize and normalize
                img_resized = cv2.resize(img, (224, 224))  # Use the input shape your model expects
                img_array = img_resized / 255.0
                img_array = np.expand_dims(img_array, axis=0)

                # Predict
                prediction = model.predict(img_array)
                predicted_class = np.argmax(prediction)
                print(f"Prediction: {predicted_class}")
            else:
                print("Failed to decode image.")
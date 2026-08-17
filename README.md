# 🌱 Plant Disease Detection System

## 📌 Project Overview
The Plant Disease Detection System is an AI-based application designed to identify plant diseases from leaf images. The system uses Deep Learning and image classification to analyze plant leaves and predict the corresponding disease.

The project uses an EfficientNetV2S-based deep learning model trained to classify plant leaf images into 38 healthy and diseased classes. It also provides disease-related information and fertilizer recommendations.

## 🚀 Features
- Plant disease detection using leaf images
- Classification into 38 plant disease and healthy classes
- Deep Learning-based image classification
- ESP32-CAM image capture support
- Flask-based backend for prediction
- Displays prediction results through a web interface
- Provides fertilizer recommendations based on detected disease

## 🛠️ Technologies Used
- Python
- TensorFlow / Keras
- EfficientNetV2S
- Flask
- NumPy
- Pillow (PIL)
- HTML / CSS
- JSON
- ESP32-CAM
- PlatformIO
- VS Code

## ⚙️ System Workflow

1. ESP32-CAM captures the plant leaf image.
2. The captured image is converted/compressed into JPEG format.
3. The image is sent to the Flask server through an HTTP request.
4. The Flask application preprocesses the image.
5. The trained EfficientNetV2S model analyzes the image.
6. The model predicts the plant disease/healthy class.
7. Disease information and fertilizer recommendation are retrieved.
8. The prediction result is displayed through the web interface.

## 🧠 Machine Learning Model
The project uses a fine-tuned **EfficientNetV2S** convolutional neural network for image classification.

The model was trained using a plant disease image dataset containing **38 classes**, including both healthy and diseased plant leaves.

## 📂 Main Project Files

- `app.py` – Main application
- `flask_server.py` – Flask server and prediction API
- `train_model.py` – Model training
- `predict_from_esp.py` – Handles ESP32-CAM predictions
- `main.cpp` – ESP32-CAM implementation
- `platformio.ini` – PlatformIO configuration
- `class_labels.json` – Disease class labels
- `disease_info.json` – Disease and recommendation information
- `index.html` – Web interface

## 🎯 Applications
- Early identification of plant diseases
- Smart agriculture
- Crop health monitoring
- Assistance to farmers in disease management

## 🔮 Future Enhancements
- Mobile application integration
- Cloud-based model deployment
- Real-time field monitoring
- Support for additional crops and diseases
- Improved fertilizer and treatment recommendations

## 👩‍💻 Project Domain
Artificial Intelligence | Machine Learning | Deep Learning | Computer Vision | Smart Agriculture

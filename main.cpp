#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <HTTPClient.h>

// ======== Wi-Fi credentials ========
const char* ssid = "UdithaM35";      // <-- your WiFi SSID
const char* password = "9739697080";      // <-- your WiFi password

// ======== Flask server URL (your PC IP + Flask port) ========
const char* serverUrl = "http://10.143.57.35:5000/upload";  // <-- PC running Flask

// Web server on ESP32 (to trigger capture from Flask)
WebServer server(80);

// ======== Camera Configuration (AI Thinker ESP32-CAM) ========
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ======== Function Declaration ========
void handleCapture();

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n=== Booting ESP32-CAM for Plant Disease Detection ===");

  // ---- Connect WiFi ----
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  int attempt = 0;
  while (WiFi.status() != WL_CONNECTED && attempt < 30) {
    delay(500);
    Serial.print(".");
    attempt++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\n❌ Failed to connect to WiFi! Restarting...");
    delay(2000);
    ESP.restart();
  }

  Serial.println("\n✅ WiFi connected!");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());

  // ---- Configure Camera ----
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  Serial.println("Initializing camera...");
  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("❌ Camera init failed! Restarting...");
    delay(2000);
    ESP.restart();
  }

  // ---- Set up Web Server ----
  server.on("/capture", HTTP_GET, handleCapture);
  server.begin();

  Serial.println("✅ ESP32 Web Server started!");
  Serial.print("Use this in Flask code as ESP32_IP: http://");
  Serial.println(WiFi.localIP());
  Serial.println("====================================================");
}

// ======== Handle Capture Function ========
void handleCapture() {
  Serial.println("📸 Capture requested from Flask...");

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("❌ Camera capture failed");
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }

  Serial.printf("Captured image size: %u bytes\n", fb->len);

  HTTPClient http;
  WiFiClient client;

  // ---- Test ping to Flask ----
  HTTPClient ping;
  ping.begin(client, "http://192.168.1.102:5000/ping");  // quick test
  int pingCode = ping.GET();
  Serial.printf("Ping /ping -> %d\n", pingCode);
  if (pingCode > 0) Serial.println(ping.getString());
  ping.end();

  // ---- Send photo to Flask ----
  http.begin(client, serverUrl);
  http.setReuse(false);
  http.setTimeout(15000);  // 15s timeout
  http.addHeader("Content-Type", "image/jpeg");

  Serial.println("➡️ Sending image to Flask server...");
  int httpResponseCode = http.POST(fb->buf, fb->len);

  if (httpResponseCode > 0) {
    Serial.printf("✅ POST /upload -> %d\n", httpResponseCode);
    String response = http.getString();
    Serial.println("Flask response: " + response);
    server.send(200, "application/json", response);
  } else {
    Serial.printf("❌ Error sending photo. Code: %d (%s)\n",
                  httpResponseCode, http.errorToString(httpResponseCode).c_str());
    server.send(500, "text/plain", "Failed to send photo to Flask");
  }

  http.end();
  esp_camera_fb_return(fb);
}

void loop() {
  server.handleClient();
  delay(50);
}
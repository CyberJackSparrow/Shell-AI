#include <WiFi.h>
#include <WebSocketsClient.h>
#include <driver/i2s.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- CONFIGURATION ---
const char* ssid = "Arun's S24 FE"; //Use your Wifi Name. Make sure it is on 2.4Ghz
const char* password = "mbsk5138"; //Your Wifi password
const char* host = "172.23.194.12"; //your PC ipv4 config
const uint16_t port = 8000; // FastAPI Port

// --- I2S PINS ---
#define I2S_MIC_SCK 14
#define I2S_MIC_WS  15
#define I2S_MIC_SD  32
#define I2S_SPK_BCLK 26
#define I2S_SPK_LRC  25
#define I2S_SPK_DIN  33

// --- OLED SETUP ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

WebSocketsClient webSocket;
String currentState = "IDLE";
bool isConnected = false;

// --- I2S SETUP FUNCTIONS ---
void setupI2S() {
  // Config for Microphone (Input)
  i2s_config_t mic_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = 16000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 64
  };
  i2s_pin_config_t mic_pins = {
    .bck_io_num = I2S_MIC_SCK,
    .ws_io_num = I2S_MIC_WS,
    .data_out_num = -1,
    .data_in_num = I2S_MIC_SD
  };
  i2s_driver_install(I2S_NUM_0, &mic_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &mic_pins);

  // Config for Speaker (Output)
  i2s_config_t spk_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = 16000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 64
  };
  i2s_pin_config_t spk_pins = {
    .bck_io_num = I2S_SPK_BCLK,
    .ws_io_num = I2S_SPK_LRC,
    .data_out_num = I2S_SPK_DIN,
    .data_in_num = -1
  };
  i2s_driver_install(I2S_NUM_1, &spk_config, 0, NULL);
  i2s_set_pin(I2S_NUM_1, &spk_pins);
}

// --- WEBSOCKET EVENT HANDLER ---
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      isConnected = false;
      Serial.println("[WSc] Disconnected!");
      break;
    case WStype_CONNECTED:
      isConnected = true;
      Serial.println("[WSc] Connected to Shell Brain");
      break;
    case WStype_TEXT:
      {
        String text = (char*)payload;
        if (text.startsWith("ANIMATION:")) {
          currentState = text.substring(10);
        }
      }
      break;
    case WStype_BIN:
      // Play incoming audio bytes directly to I2S Speaker
      size_t bytes_written;
      i2s_write(I2S_NUM_1, payload, length, &bytes_written, portMAX_DELAY);
      break;
  }
}

void setup() {
  Serial.begin(115200);
  
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    for(;;);
  }
  
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 20);
  display.println("Connecting WiFi...");
  display.display();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  setupI2S();

  // Connect to the WebSocket server
  webSocket.begin(host, port, "/ws/shell");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(2000);
}

void loop() {
  webSocket.loop();

  if (isConnected) {
    // 1. Read Mic data and stream to Python
    int16_t mic_buffer[512];
    size_t bytes_read;
    i2s_read(I2S_NUM_0, &mic_buffer, sizeof(mic_buffer), &bytes_read, portMAX_DELAY);
    if (bytes_read > 0) {
      webSocket.sendBIN((uint8_t*)mic_buffer, bytes_read);
    }
  } else {
    // Show connecting status if disconnected
    display.clearDisplay();
    display.setCursor(0, 20);
    display.println("Searching for\nShell Brain...");
    display.display();
  }

  // 2. Drive the animations
  drawFace(currentState);
  delay(1); // Small yield for system stability
}

// --- YOUR EXISTING ANIMATION LOGIC ---
void drawFace(String state) {
  display.clearDisplay();
  unsigned long t = millis();
  int centerX = SCREEN_WIDTH / 2;
  int centerY = SCREEN_HEIGHT / 2;

  if (state == "IDLE") {
    bool isBlinking = (t % 3000) < 150; 
    int eyeHeight = isBlinking ? 2 : 20;
    int eyeY = isBlinking ? centerY - 1 : centerY - 10;
    display.fillRect(centerX - 30, eyeY, 15, eyeHeight, SSD1306_WHITE);
    display.fillRect(centerX + 15, eyeY, 15, eyeHeight, SSD1306_WHITE);
  } 
  else if (state == "LISTENING") {
    int radius = 13 + 3 * sin(t / 150.0); 
    display.fillCircle(centerX - 25, centerY, radius, SSD1306_WHITE);
    display.fillCircle(centerX + 25, centerY, radius, SSD1306_WHITE);
  } 
  else if (state == "THINKING") {
    int offset = 12 * sin(t / 200.0); 
    display.fillRect(centerX - 30 + offset, centerY - 5, 20, 5, SSD1306_WHITE);
    display.fillRect(centerX + 10 + offset, centerY - 5, 20, 5, SSD1306_WHITE);
  } 
  else if (state == "SPEAKING") {
    display.fillRect(centerX - 30, centerY - 20, 15, 10, SSD1306_WHITE);
    display.fillRect(centerX + 15, centerY - 20, 15, 10, SSD1306_WHITE);
    int mouthHeight = 4 + 8 * abs(sin(t / 80.0)); 
    display.fillRoundRect(centerX - 10, centerY + 5, 20, mouthHeight, 2, SSD1306_WHITE);
  }
  display.display();
}
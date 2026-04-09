#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- CONFIGURATION ---
const char* ssid = "YOUR_SSID"; //MAKE SURE TO USE A 2.4Ghz WIFI
const char* password = "YOUR_PASS";
const char* host = "XXXX"; // EXACT IP address of your PC running Python
const uint16_t port = 8080;

// --- OLED SETUP ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

WiFiClient client;
String currentState = "IDLE";

void setup() {
  Serial.begin(115200);

  // Initialize OLED
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;);
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 20);
  display.println("Connecting WiFi...");
  display.display();

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
}

void loop() {
  // Keep TCP Connection alive

  if (!client.connected()) {
    display.clearDisplay();
    display.setCursor(0, 20);
    display.println("Searching for\nShell Brain...");
    display.display();
   
    Serial.println("Connecting to Python Server...");
    if (client.connect(host, port)) {
      Serial.println("Connected!");
      currentState = "IDLE";
    } else {
      delay(2000);
      return;
    }

  }

  // Read incoming animation commands from Python
  if (client.available()) {
    String line = client.readStringUntil('\n');
    line.trim();
    if (line.startsWith("ANIMATION:")) {
      currentState = line.substring(10); // Extract state after "ANIMATION:"
    }

  }



 
  drawFace(currentState);
  
  delay(20);
}

// --- ANIMATION DRAWING FUNCTIONS ---
void drawFace(String state) {
  display.clearDisplay();
  unsigned long t = millis(); 
  int centerX = SCREEN_WIDTH / 2;
  int centerY = SCREEN_HEIGHT / 2;

  if (state == "IDLE") {
    
    bool isBlinking = (t % 3000) < 150;
    int eyeHeight = isBlinking ? 2 : 20; // Flatten eyes if blinking
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
    // Static eyes
    display.fillRect(centerX - 30, centerY - 20, 15, 10, SSD1306_WHITE);
    display.fillRect(centerX + 15, centerY - 20, 15, 10, SSD1306_WHITE);
    
    int mouthHeight = 4 + 8 * abs(sin(t / 80.0));
    
    display.fillRoundRect(centerX - 10, centerY + 5, 20, mouthHeight, 2, SSD1306_WHITE);
  }
  
  display.display();
}

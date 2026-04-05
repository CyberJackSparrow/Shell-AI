This is the upgraded `README.md`. I’ve reorganized it into a **Step-by-Step Protocol** and included a precise hardware pinout table so anyone can wire this up without blowing a capacitor.

---

# 🐚 Shell: The Pedantic AI Voice Assistant

**Shell** is a distributed AI system. It consists of a **Brain** (Python/PC) and a **Body** (ESP32 Hardware). Shell doesn't just answer questions; he judges them. Powered by **Ollama (Gemma 3)**, **Faster-Whisper**, and **Piper TTS**, this assistant offers a fully local, multi-turn conversational experience.

---

🛠️ Phase 1: Hardware & Wiring Guide
To give Shell his senses, connect your components to the ESP32 WROOM using the following pin map.

Note: Use high-quality jumper wires. I2S audio is sensitive to loose connections, and Shell will judge you for poor signal integrity.

📺 SSD1306 OLED (The Eyes)
VCC —> ESP32 3V3 (Do NOT use 5V)

GND —> ESP32 GND

SDA —> ESP32 GPIO 21

SCL —> ESP32 GPIO 22

🎙️ INMP441 Microphone (The Ears)
VCC —> ESP32 3V3

GND —> ESP32 GND

L/R —> ESP32 GND (Sets to Left Channel)

SCK —> ESP32 GPIO 14

WS —> ESP32 GPIO 15

SD —> ESP32 GPIO 32

🔊 MAX98357A Amplifier (The Mouth)
VIN —> ESP32 5V / VIN

GND —> ESP32 GND

BCLK —> ESP32 GPIO 26

LRC —> ESP32 GPIO 25

DIN —> ESP32 GPIO 33

💡 Pro-Tips for the Build:
Power Stability: If the OLED flickers when Shell starts speaking, add a small electrolytic capacitor (10µF - 100µF) between the 3V3 and GND rails.

Microphone Orientation: The INMP441 is "bottom-ported." Ensure the tiny hole on the bottom of the chip isn't covered by tape or hot glue, or Shell will be functionally deaf.

I2S Length: Keep the wires between the Mic/Amp and the ESP32 as short as possible to prevent audio noise.

---



## 💻 Phase 2: The Brain Setup (PC)

### 1. The NVIDIA Protocol (CUDA)
Shell requires a GPU to "think" in real-time. Without CUDA, the Speech-to-Text will be painfully slow.
1. Download [NVIDIA CUDA Toolkit v12.3](https://developer.nvidia.com/cuda-12-3-0-download-archive).
2. Run the installer. Select **Custom Installation** and ensure **Runtime** and **Development** are checked.
3. Restart your PC after installation.

### 2. The Intelligence (Ollama)
1. Install [Ollama](https://ollama.com/).
2. Open your terminal and type: `ollama run gemma3:4b`.
3. Verify it's working by visiting `http://localhost:11434` in your browser. You should see *"Ollama is running"*.

### 3. Python Environment
Clone the repo and install the libraries:
```bash
git clone https://github.com/YOUR_USERNAME/Shell-AI.git
cd Shell-AI
pip install fastapi uvicorn websockets faster-whisper webrtcvad requests numpy
```

---

## 🤖 Phase 3: The Body Setup (ESP32)

### 1. Get your Brain's Address
Your ESP32 needs to know your PC's IP address.
1. Open **Command Prompt** (cmd) on your PC.
2. Type `ipconfig` and hit Enter.
3. Find your **IPv4 Address** (likely `192.168.x.x`).

### 2. Flash the ESP32
1. Open the `.ino` file in **Arduino IDE**.
2. **Library Manager:** Install `WebSockets` (by Markus Sattler), `Adafruit SSD1306`, and `Adafruit GFX`.
3. **Change the Code:**
   * Update `ssid` and `password` with your Wi-Fi details.
   * Update `host` with your **IPv4 Address** from Step 1.
4. **Upload:** Select **DOIT ESP32 DEVKIT V1** as your board.
   * *Note: If the upload hangs at "Connecting...", hold the **BOOT** button on your ESP32 until it starts writing.*

---

## 🚀 Phase 4: Operational Protocol

1. **Start the Brain:** Run `python server.py` on your PC.
2. **Boot the Body:** Power your ESP32. The OLED will show "Searching for Shell Brain...".
3. **Synchronization:** Once connected, the OLED will show Shell's Idle face (eyes).
4. **Conversation:** * Say **"Hey Shell"**. 
   * He will acknowledge you. 
   * Ask your question. He will remember the context as long as you keep talking. 
   * If you stop talking for 6 seconds, he returns to Standby.

---

## 🩺 Troubleshooting

* **"cuBLAS error":** Your CUDA installation is either missing or the wrong version. Re-install v12.3.
* **OLED is blank:** Check your SDA/SCL pins. Ensure you used the `0x3C` I2C address in the code.
* **No Sound:** Ensure the MAX98357A is getting 5V/VIN power. Check your `DIN` pin connection.
* **"Connection Refused":** Ensure your PC and ESP32 are on the **exact same Wi-Fi**. Check that your Windows Firewall isn't blocking Port 8000.

---
*Created by Arun Aditya Dey*

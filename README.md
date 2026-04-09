This is the upgraded `README.md`. I’ve reorganized it into a **Step-by-Step Protocol** and included a precise hardware pinout table so anyone can wire this up without blowing a capacitor.

---

🐚 Shell: The Pedantic AI Voice Assistant
Shell is a distributed AI system consisting of a Brain (Python/PC) and a Body (ESP32 Hardware). Shell doesn't just answer questions; he judges them. Powered by Ollama (Gemma 3), Faster-Whisper, and Piper TTS, this assistant offers a fully local, multi-turn conversational experience.

Note: This project is modular. You can start with just an ESP32 and an OLED display (using your PC's Mic/Speakers) and later upgrade to full standalone audio hardware.

🛠️ Phase 1: Hardware & Wiring Guide
1. Core Setup (Required for Animations)
To see Shell's facial expressions, connect your OLED to the ESP32:

📺 SSD1306 OLED (The Eyes)

VCC —> ESP32 3V3 (Do NOT use 5V)

GND —> ESP32 GND

SDA —> ESP32 GPIO 21

SCL —> ESP32 GPIO 22

2. Voice Expansion (Optional Upgrade)
To move the "Ears and Mouth" from your PC to the ESP32 hardware, add these I2S modules:

🎙️ INMP441 Microphone (The Ears)

VCC —> ESP32 3V3

GND —> ESP32 GND

L/R —> ESP32 GND

SCK —> ESP32 GPIO 14

WS —> ESP32 GPIO 15

SD —> ESP32 GPIO 32

🔊 MAX98357A Amplifier (The Mouth)

VIN —> ESP32 5V / VIN

GND —> ESP32 GND

BCLK —> ESP32 GPIO 26

LRC —> ESP32 GPIO 25

DIN —> ESP32 GPIO 33

💻 Phase 2: The Brain Setup (PC)
1. The NVIDIA Protocol (CUDA)
Shell requires a GPU to "think" in real-time. Without CUDA, Speech-to-Text will be painfully slow.

Download NVIDIA CUDA Toolkit v12.3.

Run the installer. Select Custom Installation and ensure Runtime and Development are checked.

Restart your PC after installation.

2. The Intelligence (Ollama)
Install Ollama.

Open your terminal and type: ollama run gemma3:4b.

Verify it's working by visiting http://localhost:11434 in your browser.

3. Python Environment
Clone the repo and install the libraries:

Bash
git clone https://github.com/YOUR_USERNAME/Shell-AI.git
cd Shell-AI
pip install fastapi uvicorn websockets faster-whisper webrtcvad requests numpy
🎙️ Phase 3: Piper TTS & Voice Setup
Shell's voice is powered by Piper, a fast local neural TTS engine.

Download Piper: Get piper_windows_amd64.zip. Unblock the zip in Properties before extracting.

Download Ryan Voice Model:

en_US-ryan-high.onnx

en_US-ryan-high.onnx.json

Organize Directory:

Plaintext
Shell-AI/
├── server.py
├── piper/
│   ├── piper.exe
│   └── models/
│       ├── en_US-ryan-high.onnx
│       └── en_US-ryan-high.onnx.json
🤖 Phase 4: The Body Setup (ESP32)
Get Brain's Address: Open cmd, type ipconfig, and find your IPv4 Address (e.g., 192.168.1.15).

Flash the ESP32:

Open the .ino file in Arduino IDE.

Install libraries: WebSockets (Markus Sattler), Adafruit SSD1306, Adafruit GFX.

Update ssid, password, and host (your IPv4) in the code.

Upload to DOIT ESP32 DEVKIT V1.

🚀 Phase 5: Operational Protocol
Start the Brain: Run python server.py.

Boot the Body: Power your ESP32. OLED should show "Searching for Shell Brain...".

Sync: Once the face appears, say "Hey Shell".

Conversation: * If using Core Setup: Speak into your PC Mic; sound comes from PC Speakers.

If using Voice Expansion: Speak into the INMP441; sound comes from the I2S Speaker.

🩺 Troubleshooting
"cuBLAS error": Re-install CUDA Toolkit v12.3 specifically.

OLED is blank: Check SDA/SCL wiring and ensure I2C address is 0x3C.

No Sound (PC Mode): Ensure sounddevice is targeting your correct default audio device.

Laggy Animations: Ensure your PC and ESP32 are on the exact same 2.4GHz Wi-Fi network.

Created by Arun Aditya Dey
Jabalpur Engineering College

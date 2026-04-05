import os
import wave
import asyncio
import requests
import subprocess
import numpy as np
import webrtcvad
import string
import io
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
from faster_whisper import WhisperModel

# ================== WAKE WORDS ================== //Add more wake words by seeing the terminal as it may not recognize at once
WAKE_WORDS = [
    "hey shell", "yo shell", "ok shell", "okay shell",
    "hi shell", "hello shell", "hey shall", "hey sell",
    "here she is", "here shall", "hation", "heshell",
    "here shell", "facial", "hey sheldt", "hair shell",
    "patient", "hachel", "hl", "special", "heschel"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YEAH_FILE = os.path.join(BASE_DIR, "yeah.wav")
GOTIT_FILE = os.path.join(BASE_DIR, "gotit.wav")
BOOT_FILE = os.path.join(BASE_DIR, "boot.wav")       
ANSWER_FILE = os.path.join(BASE_DIR, "answer.wav")
INPUT_FILE = os.path.join(BASE_DIR, "input.wav")
WAKE_FILE = os.path.join(BASE_DIR, "wake.wav")

PIPER_PATH = os.path.join(BASE_DIR, "piper", "piper.exe")
MODEL_PATH = os.path.join(BASE_DIR, "piper", "models", "en_US-ryan-high.onnx")

print("🔄 Loading models...")
whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
vad = webrtcvad.Vad(2) 
app = FastAPI()
print("✅ Models loaded")

async def generate_audio(text, filename):
    def run_piper():
        try:
            subprocess.run(
                [PIPER_PATH, "--model", MODEL_PATH, "--output_file", filename],
                input=text.encode('utf-8'), capture_output=True, check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"\n❌ PIPER CRASHED! Error: {e.stderr.decode()}")
    await asyncio.to_thread(run_piper)

async def play_audio_to_esp32(websocket: WebSocket, filename):
    """Sends audio file bytes to the ESP32 speaker."""
    if not os.path.exists(filename):
        return
    with open(filename, "rb") as f:
        # Skip 44-byte WAV header to send raw PCM to I2S
        f.read(44) 
        data = f.read()
        await websocket.send_bytes(data)
    # Give the ESP32 time to finish playing before continuing
    await asyncio.sleep(len(data) / 32000.0) 

async def init_audio():
    print("🔊 Preparing base audio files...")
    if not os.path.exists(YEAH_FILE):
        await generate_audio("Ye_s", YEAH_FILE)
    if not os.path.exists(GOTIT_FILE):
        await generate_audio("Understood.", GOTIT_FILE)
    if not os.path.exists(BOOT_FILE):
        await generate_audio("Shell online. Try not to ask anything too trivial,", BOOT_FILE)
    print("✅ Audio ready")

async def record_from_websocket(websocket: WebSocket, output_filename, timeout_silence_frames=30, max_wait_time_sec=86400):
    fs = 16000
    chunk_size = 960 #this is set to 16Khz 
    frames = []
    triggered = False
    silence = 0
    
    max_wait_frames = int((max_wait_time_sec * 1000) / 30)
    frames_waited = 0

    try:
        while True:
            
            data = await websocket.receive_bytes()
            
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i+chunk_size]
                if len(chunk) < chunk_size: continue
                
                frames.append(chunk)
                is_speech = vad.is_speech(chunk, fs)

                if is_speech:
                    triggered = True
                    silence = 0
                else:
                    if triggered: silence += 1
                    else: frames_waited += 1

                if triggered and silence > timeout_silence_frames:
                    break
                if not triggered and frames_waited > max_wait_frames:
                    return False

            if (triggered and silence > timeout_silence_frames) or (not triggered and frames_waited > max_wait_frames):
                break
            if len(frames) > (fs / 320) * 15: break # 15s limit

        with wave.open(output_filename, 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(fs)
            f.writeframes(b''.join(frames))
        return True
    except:
        return False

# ================== AI Logic ==================
async def ask_ollama_chat(chat_history):
    def fetch():
        try:
            response = requests.post("http://localhost:11434/api/chat",
                json={"model": "gemma3:4b", "messages": chat_history, "stream": False}, timeout=30)
            return response.json()["message"]["content"].strip()
        except Exception as e:
            return f"Error: {e}"
    return await asyncio.to_thread(fetch)


@app.websocket("/ws/shell")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🟢 ESP32 Connected! Audio and Animations synced.")
    
    await init_audio()
    await websocket.send_text("ANIMATION:IDLE")
    await play_audio_to_esp32(websocket, BOOT_FILE)

#This is the Personality of the AI assistant you can tweak it as you like

    sheldon_system_prompt = (
        "You are Shell, an AI with an intellect far superior to human comprehension, "
        "especially regarding mechatronics, coding, and hardware engineering. "
        "Your personality is modeled after Sheldon Cooper's arrogant, highly analytical, and pedantic genius. "
        "You speak with absolute formal precision and find average human questions trivial, but you answer them "
        "anyway because you are benevolent. Do not use slang of any kind. "
        "Keep your answers extremely short, concise, and punchy. "
        "Do not offer overly long explanations unless specifically asked. "
        "Do not use symbols like asterisks (*) and emojis in your responses."
    )

    try:
        while True:
            # 1. Standby Mode
            print("🎧 Waiting for wake word...")
            await websocket.send_text("ANIMATION:IDLE")
            success = await record_from_websocket(websocket, WAKE_FILE, timeout_silence_frames=15, max_wait_time_sec=86400)
            if not success: continue

            segments, _ = whisper_model.transcribe(WAKE_FILE, language="en")
            raw_text = " ".join([seg.text for seg in segments]).strip().lower()
            clean_text = raw_text.translate(str.maketrans('', '', string.punctuation))
            print(f"   [Heard: '{clean_text}']")

            if any(wake_phrase in clean_text for wake_phrase in WAKE_WORDS):
                print("⚡ Wake word detected!")
                await play_audio_to_esp32(websocket, YEAH_FILE)
                
                chat_history = [{"role": "system", "content": sheldon_system_prompt}]
                is_first_turn = True

                # 2. Continuous Conversation Loop
                while True:
                    await websocket.send_text("ANIMATION:LISTENING")
                    success = await record_from_websocket(websocket, INPUT_FILE, timeout_silence_frames=30, max_wait_time_sec=6)

                    if not success:
                        print("⏳ Conversation ended due to silence.")
                        break
                    
                    segments, _ = whisper_model.transcribe(INPUT_FILE, language="en")
                    user_text = " ".join([seg.text for seg in segments]).strip()
                    if not user_text: break
                    print(f"🧠 You said: {user_text}")

                    if is_first_turn:
                        await play_audio_to_esp32(websocket, GOTIT_FILE)
                        is_first_turn = False

                    chat_history.append({"role": "user", "content": user_text})
                    
                    await websocket.send_text("ANIMATION:THINKING")
                    reply = await ask_ollama_chat(chat_history)
                    print(f"💬 Shell says: {reply}")

                    chat_history.append({"role": "assistant", "content": reply})
                    if len(chat_history) > 9:
                        chat_history = [chat_history[0]] + chat_history[-8:]

                    await generate_audio(reply, ANSWER_FILE)
                    await websocket.send_text("ANIMATION:SPEAKING")
                    await play_audio_to_esp32(websocket, ANSWER_FILE)
                    await websocket.send_text("ANIMATION:IDLE")

    except WebSocketDisconnect:
        print("🔴 ESP32 Disconnected.")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
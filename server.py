import os

from pickle import FALSE

import time

import wave

import requests

import subprocess

import sounddevice as sd

import soundfile as sf

import numpy as np

import webrtcvad

import string

import socket

import threading

from faster_whisper import WhisperModel



# ================== TCP SERVER FOR ESP32 ==================

connected_clients = []



def tcp_server_loop():

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.bind(("0.0.0.0", 8080))

    server.listen(5)

    print("🌐 Network Server running on port 8080. Waiting for ESP32...")

    while True:

        client, addr = server.accept()

        print(f"🔌 ESP32 OLED Connected from {addr}")

        connected_clients.append(client)



threading.Thread(target=tcp_server_loop, daemon=True).start()



def set_animation(state):

    """Prints the state locally and broadcasts it to the ESP32."""

    print(f"\n[ANIMATION: {state}]")

    msg = f"ANIMATION:{state}\n".encode('utf-8')

    for c in list(connected_clients):

        try:

            c.sendall(msg)

        except Exception:

            connected_clients.remove(c)



# ================== CONFIGURATION ==================

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



# ================== LOAD MODELS ==================

print("🔄 Loading models...")

whisper_model = WhisperModel("base", device="cuda", compute_type="float16")

vad = webrtcvad.Vad(2)

print("✅ Models loaded")



# ================== AUDIO HELPERS ==================

def generate_audio(text, filename):

    try:

        subprocess.run(

            [PIPER_PATH, "--model", MODEL_PATH, "--output_file", filename],

            input=text.encode('utf-8'),

            capture_output=True,

            check=True

        )

    except subprocess.CalledProcessError as e:

        print(f"\n❌ PIPER CRASHED! Error details:\n{e.stderr.decode()}")



def play_audio(filename):

    if not os.path.exists(filename):

        return

    data, samplerate = sf.read(filename)

    sd.play(data, samplerate)

    sd.wait()



def init_audio():

    print("🔊 Preparing base audio files...")

    if not os.path.exists(YEAH_FILE):

        generate_audio("Ye_s", YEAH_FILE)

    if not os.path.exists(GOTIT_FILE):

        generate_audio("Understood.", GOTIT_FILE)

    if not os.path.exists(BOOT_FILE):

        generate_audio("Shell online. Try not to ask anything too trivial,", BOOT_FILE)

    print("✅ Audio ready")



# ================== RECORDING LOGIC (VAD) ==================

def record_until_silence(output_filename, timeout_silence_frames=30, max_wait_time_sec=86400):

    """Records audio. If no speech is heard within max_wait_time_sec, it times out and returns False."""

    fs = 16000

    chunk_size = 480

    frames = []

    triggered = False

    silence = 0

   

    # Calculate how many silent frames equal our timeout limit

    max_wait_frames = int((max_wait_time_sec * 1000) / 30)

    frames_waited = 0



    stream = sd.RawInputStream(samplerate=fs, blocksize=chunk_size, dtype='int16', channels=1)



    with stream:

        while True:

            data, _ = stream.read(chunk_size)

            frames.append(data)



            is_speech = vad.is_speech(data, fs)



            if is_speech:

                triggered = True

                silence = 0

            else:

                if triggered:

                    silence += 1

                else:

                    frames_waited += 1



            # Stop recording if we heard someone speak, and then they stopped

            if triggered and silence > timeout_silence_frames:

                break

           

            # 🔥 THE TIMEOUT FIX: If we wait too long without hearing a single word, abort

            if not triggered and frames_waited > max_wait_frames:

                return False

           

            # Absolute max recording time to prevent infinite loops (15 seconds)

            if len(frames) > (fs / chunk_size) * 15:

                break



    with wave.open(output_filename, 'wb') as f:

        f.setnchannels(1)

        f.setsampwidth(2)

        f.setframerate(fs)

        f.writeframes(b''.join(frames))

       

    return True



# ================== WAKE WORD ==================

def wait_for_wake_word():

    set_animation("IDLE")

    print(f"🎧 Waiting for wake word (e.g., '{WAKE_WORDS[0]}')...")

   

    while True:

        # Pass a massive wait time so it listens for the wake word forever

        success = record_until_silence(WAKE_FILE, timeout_silence_frames=15, max_wait_time_sec=86400)

        if not success: continue



        segments, _ = whisper_model.transcribe(WAKE_FILE, language="en")

        raw_text = " ".join([seg.text for seg in segments]).strip()



        if not raw_text:

            continue



        clean_text = raw_text.translate(str.maketrans('', '', string.punctuation)).lower()

        print(f"   [Heard: '{clean_text}']")



        if any(wake_phrase in clean_text for wake_phrase in WAKE_WORDS):

            print("⚡ Wake word detected!")

            return True



# ================== LISTEN ==================

def listen_for_command(wait_timeout=6):

    set_animation("LISTENING")

    print(f"🎤 Listening... (will time out in {wait_timeout} seconds if silent)")

   

    # Wait for up to 6 seconds for the user to reply. If silent, return False

    success = record_until_silence(INPUT_FILE, timeout_silence_frames=30, max_wait_time_sec=wait_timeout)

   

    if not success:

        return "" # The user went silent

   

    segments, _ = whisper_model.transcribe(INPUT_FILE, language="en")

    text = " ".join([seg.text for seg in segments]).strip()

   

    print(f"🧠 You said: {text}")

    return text



# ================== AI ==================

def ask_ollama_chat(chat_history):

    set_animation("THINKING")

    print("🤖 Shell is thinking...")

   

    try:

        # Notice we are now using /api/chat instead of /api/generate

        response = requests.post(

            "http://localhost:11434/api/chat",

            json={

                "model": "gemma3:4b",

                "messages": chat_history,

                "stream": False

            },

            timeout=30

        )

        return response.json()["message"]["content"].strip()

    except Exception as e:

        print(f"⚠️ Ollama error: {e}")

        return "It appears my superior architecture cannot connect to the local server at this moment."



# ================== MAIN LOOP ==================

def assistant_loop():

    init_audio()

    play_audio(BOOT_FILE)

    print(f"🤖 System fully active. Say '{WAKE_WORDS[0]}' to start.")

   

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



    while True:

        # 1. Standby Mode

        wait_for_wake_word()

        play_audio(YEAH_FILE)

       

        # 2. Start a fresh conversation memory block

        chat_history = [

            {"role": "system", "content": sheldon_system_prompt}

        ]

        is_first_turn = True



        # 3. The Continuous Conversation Loop

        while True:

            # Shell waits 6 seconds for you to speak. If you don't, it times out.

            user_text = listen_for_command(wait_timeout=6)



            # If silence is detected, break out of this inner loop and return to wake word

            if not user_text:

                print("⏳ Conversation ended due to silence. Returning to standby.")

                break

            if is_first_turn:

                play_audio(GOTIT_FILE)

                is_first_turn = False



            # Add user's question to the memory

            chat_history.append({"role": "user", "content": user_text})



            # Get reply using the full history

            reply = ask_ollama_chat(chat_history)

            print(f"💬 Shell says: {reply}")



            # Add AI's answer to the memory

            chat_history.append({"role": "assistant", "content": reply})

           

            # Keep the history array from getting too massive and crashing the API

            # Keep the system prompt [0] and the last 4 exchanges (8 messages)

            if len(chat_history) > 9:

                chat_history = [chat_history[0]] + chat_history[-8:]



            generate_audio(reply, ANSWER_FILE)

            set_animation("SPEAKING")

            play_audio(ANSWER_FILE)

            set_animation("IDLE")



            # Do NOT sleep here anymore. Loop instantly back to listening!



# ================== RUN ==================

if __name__ == "__main__":

    assistant_loop()

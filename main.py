import os
import time
import redis
import threading
import base64
import io
import re
from PIL import ImageGrab, Image
import assemblyai as aai
import pyperclip

count = 0
combined_text = ""
my_prompt = """System Prompt (concise):
In a C# interview, give concise answers. For definitions or differences, use one line 
plus a real-life example. Share code only if asked, and avoid Dictionary examples unless 
specifically requested. Coding explanations should be clear but brief. If only theory is 
needed, don't include code. Keep responses simple, precise, and practical."""
no_of_question_sent = 0

# --- Redis Config ---
r = redis.Redis(
    host='redis-10748.c330.asia-south1-1.gce.redns.redis-cloud.com',
    port=10748,
    decode_responses=True,
    username="default",
    password="0LOOmEVVY2jnAUieXYIV5kv7rZhx7ItL",
)

channel = "realtime:channel"
r.publish(channel, my_prompt)

# --- AssemblyAI Config ---
aai.settings.api_key = "e8349e0c311e419ab4a0993dcade5866"
SILENCE_THRESHOLD = 0.7  # 700ms

# --- State ---
transcription = ""
sent_length = 0
last_update_time = time.time()
screenshots_buffer = []
screenshot_lock = threading.Lock()


def redis_subscriber():
    try:
        pubsub = r.pubsub()
        pubsub.subscribe("realtime:alerts")

        print("📡 Listening to 'realtime:alerts'...")
        for message in pubsub.listen():
            if message and message['type'] == 'message':
                data = message['data']
                if isinstance(data, bytes):
                    data = data.decode().strip().lower()

                print(f"🔴 Raw Redis message: {data}")

                if data == "screenshot":
                    print("🖼️ Triggering capture from Redis message")
                    capture_and_buffer_screenshot()
                if data.strip().lower() == "clipboard":
                    print("📥 Clipboard fetch requested.")
                    try:
                        clipboard_text = pyperclip.paste()
                        if clipboard_text.strip():
                            r.publish(channel, clipboard_text)
                            print(f"📤 Clipboard sent: {clipboard_text[:50]}{'...' if len(clipboard_text) > 50 else ''}")
                        else:
                            print("📤 Clipboard is empty.")
                    except Exception as e:
                        print(f"❌ Clipboard read error: {e}")
    except Exception as e:
        print(f"❌ Redis subscriber error: {e}")


# ----------------- Screenshot Processing Functions -----------------
def convert_screenshot_to_base64(screenshot):
    """Convert PIL Image to base64 string"""
    try:
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return img_base64
    except Exception as e:
        print(f"❌ Error converting screenshot: {e}")
        return None


# ----------------- Screenshot Handling -----------------
def capture_and_buffer_screenshot():
    global combined_text
    global count
    try:
        with screenshot_lock:
            screenshot = ImageGrab.grab()
            count += 1

            # Convert screenshot to base64
            img_base64 = convert_screenshot_to_base64(screenshot)
            if img_base64:
                # Create unique image ID
                image_id = f"screenshot_{int(time.time())}_{count}"

                # Store the actual image data separately in Redis
                # Set expiration to 1 hour (3600 seconds)
                r.set(f"image:{image_id}", img_base64, ex=3600)

                # Send only a reference in the main message
                message_text = f"📸 Screenshot captured: {image_id}"
                combined_text += f"\n{message_text}\n\n"
                print(f"📸 Screenshot stored with ID: {image_id} (size: {len(img_base64)} chars)")

            if count >= 2:
                print("Sending message with screenshot references...")
                if combined_text:
                    print("Sending message to Redis...")
                    r.publish(channel, combined_text)
                count = 0
                combined_text = ""

    except Exception as e:
        print(f"❌ Error capturing screenshot: {e}")


# ----------------- Transcription Handling -----------------
def paste_and_send():
    global sent_length, transcription, last_update_time, no_of_question_sent, my_prompt
    new_text = transcription[sent_length:]

    if new_text:
        if no_of_question_sent == 5:
            r.publish(channel, my_prompt)
            no_of_question_sent = 0
        r.publish(channel, new_text.encode("utf-8"))
        print(f"🗣️ Sent transcription: {new_text.strip()}")
        sent_length = len(transcription)
        last_update_time = time.time()
        no_of_question_sent += 1


def on_data(transcript: aai.RealtimeTranscript):
    global transcription, last_update_time

    if not transcript.text:
        return

    if isinstance(transcript, aai.RealtimeFinalTranscript):
        transcription += transcript.text + " "
        last_update_time = time.time()


def on_error(error: aai.RealtimeError):
    print("❌ Transcription error:", error)


def on_open(session_opened: aai.RealtimeSessionOpened):
    print("🔓 Session ID:", session_opened.session_id)


def on_close():
    print("🔒 Session closed.")


# ----------------- Start Transcription -----------------
def start_transcription():
    transcriber = aai.RealtimeTranscriber(
        sample_rate=44100,
        on_data=on_data,
        on_error=on_error,
        on_open=on_open,
        on_close=on_close,
        end_utterance_silence_threshold=950
    )
    transcriber.connect()
    microphone_stream = aai.extras.MicrophoneStream(sample_rate=44100, device_index=1)
    transcriber.stream(microphone_stream)


# ----------------- Monitor Clipboard (Text Trigger) -----------------
def monitor_transcription():
    global transcription, last_update_time, sent_length
    while True:
        current_time = time.time()
        new_text = transcription[sent_length:]
        new_words = new_text.split()
        if (new_text and current_time - last_update_time > SILENCE_THRESHOLD) or len(new_words) >= 7:
            paste_and_send()
        time.sleep(0.1)


# ----------------- Main -----------------
def main():
    threading.Thread(target=start_transcription, daemon=True).start()
    threading.Thread(target=monitor_transcription, daemon=True).start()
    threading.Thread(target=redis_subscriber, daemon=True).start()  # NEW THREAD
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()

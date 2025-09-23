import os
import time
import redis
import threading
import base64
import io
import re
import configparser
import logging
import sys
from datetime import datetime
from PIL import ImageGrab, Image
import assemblyai as aai
import pyperclip

# Setup logging
def setup_logging():
    """Setup logging for both console and file output"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Setup logging format with more detailed timestamp
    log_format = '%(asctime)s | %(levelname)-8s | %(message)s'
    
    # Create file handler with explicit encoding and flushing
    log_filename = f'logs/speech2text_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log filename is handled automatically
    
    return root_logger

# Initialize logging
logger = setup_logging()
logger.info("🚀 Speech2Text Service Starting...")

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')
logger.info("📋 Configuration loaded from config.ini")

# Get Redis configuration
redis_host = config.get('REDIS', 'host')
redis_port = config.getint('REDIS', 'port')
redis_username = config.get('REDIS', 'username')
redis_password = config.get('REDIS', 'password')
logger.info(f"🔧 Redis configured: {redis_host}:{redis_port}")

# Get AssemblyAI configuration
assemblyai_api_key = config.get('ASSEMBLYAI', 'api_key')
logger.info(f"🎤 AssemblyAI configured: {assemblyai_api_key[:10]}...")

# Get system prompt configuration
my_prompt = config.get('PROMPT', 'system_prompt')
logger.info("📝 System prompt loaded from configuration")

count = 0
combined_text = ""
no_of_question_sent = 0

# --- Redis Config ---
r = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username=redis_username,
    password=redis_password,
)

channel = "realtime:channel"
r.publish(channel, my_prompt)
logger.info(f"📤 SYSTEM PROMPT: Initial prompt sent to Redis channel '{channel}'")

# --- AssemblyAI Config ---
aai.settings.api_key = assemblyai_api_key
SILENCE_THRESHOLD = 0.4  # 700ms

# --- State ---
transcription = ""
sent_length = 0
last_update_time = time.time()
screenshots_buffer = []
screenshot_lock = threading.Lock()

# --- Speech Control State ---
speech_enabled = False
speech_lock = threading.Lock()
transcriber = None
microphone_stream = None
transcription_thread = None
monitor_thread = None


def redis_subscriber():
    global speech_enabled
    try:
        pubsub = r.pubsub()
        pubsub.subscribe("realtime:alerts")

        logger.info("📡 Listening to 'realtime:alerts'...")
        for message in pubsub.listen():
            if message and message['type'] == 'message':
                data = message['data']
                if isinstance(data, bytes):
                    data = data.decode().strip().lower()

                logger.debug(f"🔴 Raw Redis message: {data}")

                # Handle speech control commands
                if data == "start speech":
                    logger.info("🎤 Starting speech recognition from Redis command")
                    start_speech_service()
                elif data == "stop speech":
                    logger.info("🛑 Stopping speech recognition from Redis command")
                    stop_speech_service()
                elif data == "screenshot":
                    logger.info("🖼️ Triggering capture from Redis message")
                    capture_and_buffer_screenshot()
                elif data.strip().lower() == "clipboard":
                    logger.info("📥 Clipboard fetch requested.")
                    try:
                        clipboard_text = pyperclip.paste()
                        if clipboard_text.strip():
                            r.publish(channel, clipboard_text)
                            logger.info(f"📋 CLIPBOARD: {clipboard_text.strip()}")
                            logger.info(f"📤 Clipboard sent: {clipboard_text[:50]}{'...' if len(clipboard_text) > 50 else ''}")
                        else:
                            logger.info("📤 Clipboard is empty.")
                    except Exception as e:
                        logger.error(f"❌ Clipboard read error: {e}")
    except Exception as e:
        logger.error(f"❌ Redis subscriber error: {e}")


# ----------------- Speech Control Functions -----------------
def start_speech_service():
    """Start the speech recognition service"""
    global speech_enabled, transcriber, microphone_stream, transcription_thread, monitor_thread

    with speech_lock:
        if speech_enabled:
            print("⚠️ Speech service is already running")
            return

        try:
            speech_enabled = True

            # ⭐ ADD THIS LINE - Send status to speech status channel
            r.publish("speech:status", "SPEECH_STARTED")

            # Start transcription in a new thread
            transcription_thread = threading.Thread(target=start_transcription, daemon=True)
            transcription_thread.start()

            # Start monitoring in a new thread
            monitor_thread = threading.Thread(target=monitor_transcription, daemon=True)
            monitor_thread.start()

            logger.info("🎤 SPEECH SERVICE: Started successfully")
            print("✅ Speech recognition service started")

        except Exception as e:
            speech_enabled = False
            print(f"❌ Failed to start speech service: {e}")
            r.publish(channel, f"❌ Failed to start speech service: {e}")
            # ⭐ ADD THIS LINE - Send failure status
            r.publish("speech:status", "SPEECH_STOPPED")


def stop_speech_service():
    """Stop the speech recognition service"""
    global speech_enabled, transcriber, microphone_stream

    with speech_lock:
        if not speech_enabled:
            print("⚠️ Speech service is not running")
            return

        try:
            speech_enabled = False

            # ⭐ ADD THIS LINE - Send status to speech status channel
            r.publish("speech:status", "SPEECH_STOPPED")

            # Close transcriber connection
            if transcriber:
                try:
                    transcriber.close()
                    print("🔒 Transcriber connection closed")
                except Exception as e:
                    print(f"⚠️ Error closing transcriber: {e}")

            # Close microphone stream
            if microphone_stream:
                try:
                    microphone_stream.close()
                    print("🎙️ Microphone stream closed")
                except Exception as e:
                    print(f"⚠️ Error closing microphone: {e}")

            # Reset transcriber and stream
            transcriber = None
            microphone_stream = None

            logger.info("🛑 SPEECH SERVICE: Stopped successfully")
            print("✅ Speech recognition service stopped")

        except Exception as e:
            print(f"❌ Error stopping speech service: {e}")
            r.publish(channel, f"❌ Error stopping speech service: {e}")
            # ⭐ ADD THIS LINE - Ensure stopped status is sent even on error
            r.publish("speech:status", "SPEECH_STOPPED")


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
            screenshot1 = ImageGrab.grab()
            width, height = screenshot1.size
            screenshot = screenshot1.crop((0, 84, width, height - 80))

            count += 1

            # Convert screenshot to base64
            img_base64 = convert_screenshot_to_base64(screenshot)
            if img_base64:
                # Create unique image ID
                image_id = f"screenshot_{int(time.time())}_{count}"

                # Store the actual image data separately in Redis
                # Set expiration to 1 hour (60 seconds)
                r.set(f"image:{image_id}", img_base64, ex=60)

                # Send only a reference in the main message
                message_text = f"📸 Screenshot captured: {image_id}"
                combined_text += f"\n{message_text}\n\n"
                
                # Log screenshot details
                logger.info(f"📸 SCREENSHOT: {image_id} - Size: {len(img_base64)} chars - Resolution: {screenshot.size[0]}x{screenshot.size[1]}")
                print(f"📸 Screenshot stored with ID: {image_id} (size: {len(img_base64)} chars)")

            if count >= 2:
                print("Sending message with screenshot references...")
                if combined_text:
                    print("Sending message to Redis...")
                    r.publish(channel, combined_text)
                    logger.info(f"📤 SCREENSHOTS SENT: {count} screenshots sent to Redis")
                count = 0
                combined_text = ""

    except Exception as e:
        print(f"❌ Error capturing screenshot: {e}")


# ----------------- Transcription Handling -----------------
def paste_and_send():
    global sent_length, transcription, last_update_time, no_of_question_sent, my_prompt

    # Only send if speech is enabled
    if not speech_enabled:
        return

    new_text = transcription[sent_length:]

    if new_text:
        if no_of_question_sent == 5:
            r.publish(channel, my_prompt)
            logger.info(f"🔄 SYSTEM PROMPT RESENT: After {no_of_question_sent} questions")
            no_of_question_sent = 0
        r.publish(channel, new_text.encode("utf-8"))
        logger.info(f"🗣️ SPEECH: {new_text.strip()}")
        print(f"🗣️ Sent transcription: {new_text.strip()}")
        sent_length = len(transcription)
        last_update_time = time.time()
        no_of_question_sent += 1


def on_data(transcript: aai.RealtimeTranscript):
    global transcription, last_update_time

    # Only process if speech is enabled
    if not speech_enabled:
        return

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
    global transcriber, microphone_stream

    try:
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
    except Exception as e:
        print(f"❌ Error in transcription: {e}")
        # Auto-stop if there's an error
        stop_speech_service()


# ----------------- Monitor Transcription -----------------
def monitor_transcription():
    global transcription, last_update_time, sent_length

    while speech_enabled:
        try:
            current_time = time.time()
            new_text = transcription[sent_length:]
            new_words = new_text.split()
            if (new_text and current_time - last_update_time > SILENCE_THRESHOLD) or len(new_words) >= 7:
                paste_and_send()
            time.sleep(0.1)
        except Exception as e:
            print(f"❌ Error in monitor_transcription: {e}")
            break

    print("📴 Transcription monitoring stopped")


# ----------------- Main -----------------
def main():
    logger.info("🚀 Speech2Text Controllable Service Starting...")
    logger.info("📡 Listening for Redis commands: 'start speech', 'stop speech', 'screenshot', 'clipboard'")

    # Start Redis subscriber
    threading.Thread(target=redis_subscriber, daemon=True).start()
    logger.info("🔄 Redis subscriber thread started")

    # Keep the main thread alive
    try:
        logger.info("✅ Service is now running and ready to receive commands")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down service...")
        stop_speech_service()
        logger.info("👋 Service stopped.")


if __name__ == "__main__":
    main()

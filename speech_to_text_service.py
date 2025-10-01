import os
import time
import redis
import threading
import configparser
import logging
import sys
from datetime import datetime
import assemblyai as aai

# Setup logging
def setup_logging():
    """Setup logging for both console and file output"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    log_format = '%(asctime)s | %(levelname)-8s | %(message)s'
    log_filename = f'logs/speech2text_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
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

# --- Redis Config ---
r = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username=redis_username,
    password=redis_password,
)

channel = "realtime:channel"

# --- AssemblyAI Config ---
aai.settings.api_key = assemblyai_api_key
SILENCE_THRESHOLD = 0.4  # 700ms

# --- State ---
transcription = ""
sent_length = 0
last_update_time = time.time()

# --- Speech Control State ---
speech_enabled = False
speech_lock = threading.Lock()
transcriber = None
microphone_stream = None
transcription_thread = None
monitor_thread = None


def redis_subscriber():
    """Listen for Redis commands to start/stop speech"""
    global speech_enabled
    try:
        pubsub = r.pubsub()
        pubsub.subscribe("realtime:alerts")

        logger.info("📡 Listening to 'realtime:alerts' for speech commands...")
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
    except Exception as e:
        logger.error(f"❌ Redis subscriber error: {e}")


def start_speech_service():
    """Start the speech recognition service"""
    global speech_enabled, transcriber, microphone_stream, transcription_thread, monitor_thread

    with speech_lock:
        if speech_enabled:
            print("⚠️ Speech service is already running")
            return

        try:
            speech_enabled = True

            # Send status to speech status channel
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

            # Send status to speech status channel
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
            r.publish("speech:status", "SPEECH_STOPPED")


def paste_and_send():
    """Send transcribed text to Redis"""
    global sent_length, transcription, last_update_time

    # Only send if speech is enabled
    if not speech_enabled:
        return

    new_text = transcription[sent_length:]

    if new_text:
        r.publish(channel, new_text.encode("utf-8"))
        logger.info(f"🗣️ SPEECH: {new_text.strip()}")
        print(f"🗣️ Sent transcription: {new_text.strip()}")
        sent_length = len(transcription)
        last_update_time = time.time()


def on_data(transcript: aai.RealtimeTranscript):
    """Handle Assembly AI transcription data"""
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


def start_transcription():
    """Start Assembly AI transcription"""
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
        stop_speech_service()


def monitor_transcription():
    """Monitor transcription and send to Redis when ready"""
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


def main():
    """Main function"""
    logger.info("🚀 Speech2Text Service Starting...")
    logger.info("📡 Listening for Redis commands: 'start speech', 'stop speech'")

    # Start Redis subscriber
    threading.Thread(target=redis_subscriber, daemon=True).start()
    logger.info("🔄 Redis subscriber thread started")

    # Keep the main thread alive in a loop
    try:
        logger.info("✅ Service is now running and ready to receive commands")
        logger.info("🔄 Service will stay running - use 'start speech' and 'stop speech' commands")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down service...")
        stop_speech_service()
        logger.info("👋 Service stopped.")


if __name__ == "__main__":
    main()

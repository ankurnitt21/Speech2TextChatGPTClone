import webbrowser
import time
import pyautogui
import pyperclip
import redis

def process_url(url, redis_client):
    """Process a single URL - open browser, copy content, close browser"""
    print(f"Processing URL: {url}")
    
    print("Opening browser...")
    # Open URL in default browser
    webbrowser.open(url)
    
    # Wait for browser to load
    time.sleep(5)
    
    print("Selecting all content...")
    # Select all content (Ctrl+A)
    pyautogui.hotkey('ctrl', 'a')
    
    # Small delay
    time.sleep(0.5)
    
    print("Copying content...")
    # Copy content (Ctrl+C)
    pyautogui.hotkey('ctrl', 'c')
    
    # Small delay
    time.sleep(1)
    
    print("Processing clipboard content...")
    # Get clipboard content
    clipboard_content = pyperclip.paste()
    
    # Split into lines and take only first 100 lines
    lines = clipboard_content.split('\n')
    limited_lines = lines[:100]
    
    # Join back and set to clipboard
    limited_content = '\n'.join(limited_lines)
    pyperclip.copy(limited_content)
    
    print("Closing browser...")
    # Close browser (Alt+F4)
    pyautogui.hotkey('alt', 'f4')
    
    # Send the 100 lines to Redis channel
    print("Sending content to realtime:channel...")
    try:
        redis_client.publish('realtime:channel', limited_content)
        print("Content sent to realtime:channel successfully!")
    except Exception as e:
        print(f"Failed to send content to Redis channel: {e}")
    
    print(f"Done! Copied {len(limited_lines)} lines to clipboard and sent to realtime:channel (max 100).")

def main():
    # Redis connection with hardcoded credentials
    try:
        r = redis.Redis(
            host='redis-10748.c330.asia-south1-1.gce.redns.redis-cloud.com',
            port=10748,
            username='default',
            password='0LOOmEVVY2jnAUieXYIV5kv7rZhx7ItL',
            decode_responses=True
        )
        # Test connection
        r.ping()
        print("Connected to Redis Cloud")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return
    
    # Subscribe to the channel
    channel_name = 'url_channel'
    pubsub = r.pubsub()
    pubsub.subscribe(channel_name)
    
    print(f"Listening for URLs on Redis channel '{channel_name}'...")
    print("Send a URL to the channel using: redis-cli PUBLISH url_channel 'https://example.com'")
    print("Press Ctrl+C to exit")
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                url = message['data'].strip()
                if url and url.startswith(('http://', 'https://')):
                    process_url(url, r)
                else:
                    print(f"Invalid URL received: {url}")
    except KeyboardInterrupt:
        print("\nShutting down...")
        pubsub.unsubscribe(channel_name)
        pubsub.close()

if __name__ == "__main__":
    main()


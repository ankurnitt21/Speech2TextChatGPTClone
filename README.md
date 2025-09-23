# Speech2Text Service

A real-time speech-to-text service that integrates with Redis and AssemblyAI for voice transcription, screenshot capture, and clipboard management.

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Python 3.7 or higher
- Internet connection for dependency installation

### Installation & Setup

1. **Download the files**
   - Copy all files to a folder on your computer
   - Or use the portable version (single .bat file that creates all files)

2. **Configure your credentials**
   - Edit `config.ini` with your Redis and AssemblyAI credentials

3. **Start the service**
   ```cmd
   start_service.bat
   ```

4. **Stop the service**
   ```cmd
   manage_service.bat
   ```

## 📁 Files Overview

| File | Description |
|------|-------------|
| `main.py` | Main application with speech recognition and Redis integration |
| `config.ini` | Configuration file with Redis and AssemblyAI credentials |
| `requirements.txt` | Python dependencies |
| `start_service.bat` | Starts the service in background |
| `manage_service.bat` | Stops the background service |
| `README.md` | This documentation file |

## ⚙️ Configuration

Edit `config.ini` with your credentials:

```ini
[REDIS]
host=your-redis-host.com
port=6379
username=default
password=your-redis-password

[ASSEMBLYAI]
api_key=your-assemblyai-api-key

[PROMPT]
system_prompt=Your custom AI system prompt here
```

### Getting Credentials

#### Redis Cloud
1. Go to [Redis Cloud](https://redis.com/try-free/)
2. Create a free account
3. Create a new database
4. Copy the host, port, username, and password

#### AssemblyAI
1. Go to [AssemblyAI](https://www.assemblyai.com/)
2. Sign up for a free account
3. Copy your API key from the dashboard

## 🎯 Features

### Voice Recognition
- **Real-time speech-to-text** using AssemblyAI
- **Automatic transcription** with configurable silence detection
- **Smart batching** sends text after pauses or word limits

### Redis Integration
- **Real-time communication** through Redis channels
- **Remote commands** for speech control
- **Status updates** for service monitoring

### Screenshot Capture
- **Automatic screenshot** capture and processing
- **Base64 encoding** for efficient storage
- **Redis storage** with automatic expiration

### Clipboard Management
- **Clipboard monitoring** and content sharing
- **Automatic text extraction** and transmission

### Comprehensive Logging
- **Detailed activity logs** with timestamps
- **Speech transcription** logging
- **Screenshot capture** logging
- **Clipboard activity** logging
- **Service events** logging

## 🎮 Usage

### Starting the Service

```cmd
start_service.bat
```

This will:
- Check for Python installation
- Install required dependencies automatically
- Start the service in background (hidden)
- Create log files in `logs/` directory

### Stopping the Service

```cmd
manage_service.bat
```

This will:
- Stop the background service
- Show available log files
- Clean up processes

### Redis Commands

Send these commands to the `realtime:alerts` Redis channel:

| Command | Action |
|---------|--------|
| `start speech` | Start voice recognition |
| `stop speech` | Stop voice recognition |
| `screenshot` | Capture screenshot |
| `clipboard` | Send clipboard content |

### Viewing Logs

Logs are automatically saved in the `logs/` directory with timestamps:
```
logs/speech2text_2024-01-15_14-30-25.log
```

Log entries include:
- 🗣️ **SPEECH**: Transcribed voice content
- 📸 **SCREENSHOT**: Screenshot capture details
- 📋 **CLIPBOARD**: Clipboard content
- 🎤 **SPEECH SERVICE**: Service start/stop events
- 🔄 **SYSTEM PROMPT**: AI prompt management

## 🔧 Troubleshooting

### Python Not Found
If you get "Python is not installed" error:

1. **Download Python** from [python.org](https://www.python.org/downloads/)
2. **Check "Add Python to PATH"** during installation
3. **Restart command prompt** after installation

### Service Won't Start
1. Check `config.ini` has correct credentials
2. Ensure internet connection is available
3. Check logs for error messages
4. Verify Redis server is accessible

### Dependencies Issues
If dependencies fail to install:
```cmd
pip install -r requirements.txt
```

### Service Won't Stop
If `manage_service.bat` doesn't stop the service:
1. Open Task Manager
2. Find Python processes
3. End the process manually

## 📊 Log Examples

```
2024-01-15 14:30:25,123 | INFO     | 🚀 Speech2Text Service Starting...
2024-01-15 14:30:25,156 | INFO     | 📋 Configuration loaded from config.ini
2024-01-15 14:30:45,567 | INFO     | 🎤 SPEECH SERVICE: Started successfully
2024-01-15 14:30:52,123 | INFO     | 🗣️ SPEECH: Hello, can you help me with this code?
2024-01-15 14:31:15,456 | INFO     | 📸 SCREENSHOT: screenshot_1705329075_1 - Size: 45632 chars - Resolution: 1920x1080
2024-01-15 14:31:25,234 | INFO     | 📋 CLIPBOARD: public class MyClass { }
```

## 🚀 Deployment to Another Computer

### Method 1: Copy Files
1. Copy all files to the target computer
2. Ensure Python is installed
3. Run `start_service.bat`

### Method 2: Portable Version
1. Use the portable .bat file that creates all files
2. Run it on the target computer
3. Edit `config.ini` with credentials
4. Run `start_service.bat`

## 🔒 Security Notes

- Keep your `config.ini` file secure (contains API keys and passwords)
- Don't share your AssemblyAI API key publicly
- Redis credentials should be kept confidential
- The service runs locally and doesn't expose any ports

## 📈 Performance

- **Low CPU usage** when idle
- **Minimal memory footprint** (~50-100MB)
- **Efficient logging** with automatic file rotation
- **Background operation** doesn't interfere with other applications

## 🆘 Support

If you encounter issues:

1. **Check logs** in the `logs/` directory
2. **Verify configuration** in `config.ini`
3. **Test Python installation** with `python --version`
4. **Check internet connectivity**
5. **Restart the service** (stop and start again)

## 📝 Version History

- **v1.0** - Initial release with basic speech recognition
- **v1.1** - Added Redis integration and screenshot capture
- **v1.2** - Enhanced logging and clipboard management
- **v1.3** - Background service and deployment improvements

## 📄 License

This project is for personal/educational use. Please respect the terms of service for Redis Cloud and AssemblyAI.

---

**Happy transcribing!** 🎤✨

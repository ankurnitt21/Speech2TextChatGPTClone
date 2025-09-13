import subprocess
import sys

# Function to install a package
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# List of required packages
required_packages = [
    "assemblyai",
    "assemblyai[extras]",
    "pytesseract",
    "pillow",
    "redis",
    "pyperclip",
    "pyaudio"
]

# Try importing, install if missing
for package in required_packages:
    try:
        __import__(package.split("[")[0])  # import base module name (handles extras)
        print(f"✅ {package} already installed")
    except ImportError:
        print(f"📦 Installing {package} ...")
        install(package)
        __import__(package.split("[")[0])  # import after installation

print("🚀 All dependencies are ready to use!")

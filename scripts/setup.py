#!/usr/bin/env python3
import sys
import subprocess

def main():
    print("Setting up Sentinel AI Environment...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("Successfully installed Python dependencies!")
    except Exception as e:
        print(f"Installation error: {e}")

if __name__ == "__main__":
    main()

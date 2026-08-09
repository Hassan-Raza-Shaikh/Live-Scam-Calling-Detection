#!/usr/bin/env python3
import os
import tarfile
import urllib.request
from app.utils.logger import get_logger

logger = get_logger(__name__)

MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-2023-06-26.tar.bz2"
TARGET_DIR = "models/sherpa"
ARCHIVE_NAME = "sherpa-onnx-streaming-zipformer-en-2023-06-26.tar.bz2"

def main():
    logger.info("Starting download of the English Zipformer Streaming Transducer model...")
    
    # Ensure target directory exists
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    archive_path = os.path.join(TARGET_DIR, ARCHIVE_NAME)
    
    # Download the archive
    if not os.path.exists(archive_path):
        logger.info(f"Downloading model archive from {MODEL_URL}...")
        try:
            # Show progress
            def report_hook(block_num, block_size, total_size):
                read_so_far = block_num * block_size
                if total_size > 0:
                    percent = read_so_far * 1e2 / total_size
                    print(f"\rDownloading: {percent:.1f}% ({read_so_far / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB)", end="")
                else:
                    print(f"\rDownloaded: {read_so_far / (1024*1024):.1f}MB", end="")
                    
            urllib.request.urlretrieve(MODEL_URL, archive_path, reporthook=report_hook)
            print() # Clear line
            logger.info("Download completed successfully!")
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            return
    else:
        logger.info("Model archive already exists, skipping download.")
        
    # Extract archive
    logger.info("Extracting model archive...")
    try:
        with tarfile.open(archive_path, "r:bz2") as tar:
            tar.extractall(path=TARGET_DIR)
        logger.info("Extraction completed successfully!")
    except Exception as e:
        logger.error(f"Failed to extract model: {e}")
        return
        
    # Relocate files from subdirectory to models/sherpa
    sub_dir = os.path.join(TARGET_DIR, "sherpa-onnx-streaming-zipformer-en-2023-06-26")
    if os.path.exists(sub_dir):
        logger.info(f"Relocating model files from {sub_dir} to {TARGET_DIR}...")
        for filename in os.listdir(sub_dir):
            src = os.path.join(sub_dir, filename)
            dst = os.path.join(TARGET_DIR, filename)
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
        # Clean up empty subdirectory and downloaded archive
        os.rmdir(sub_dir)
        os.remove(archive_path)
        logger.info("Cleaned up temporary directories and archive.")
    
    logger.info("ASR Model setup finished successfully!")

if __name__ == "__main__":
    main()

import time
import os
import json
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import whisper
import torch

# --- CONFIGURATION ---
# The folder where Camtasia/OBS saves your videos
WATCH_DIR = r"C:\Users\YourName\Videos\AXI_Recordings" 

# Output folder for your processed wisdom (JSON/Text)
OUTPUT_DIR = r"C:\Users\YourName\Documents\AXI_KnowledgeBase"

# Whisper Model Size: 'base', 'small', 'medium', 'large'
# 'small' is a good balance of speed and accuracy for English.
# 'medium' or 'large' is better if you have a strong GPU (Nvidia).
MODEL_SIZE = "small" 

# Supported video extensions to watch for
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv')

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("AXI_Ingestor")

class AXIVideoHandler(FileSystemEventHandler):
    """
    Watches for new video files. When one is created/modified,
    it triggers the transcription pipeline.
    """
    def __init__(self, model):
        self.model = model
        self.last_processed = {} # Debounce mechanism to prevent double-processing

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(VIDEO_EXTENSIONS):
            self.process_video(event.src_path)

    def on_modified(self, event):
        # Some recorders write to the file continuously. 
        # We need to wait until the file is "done" (size stops changing).
        if not event.is_directory and event.src_path.lower().endswith(VIDEO_EXTENSIONS):
            self.process_video(event.src_path)

    def process_video(self, file_path):
        """
        Wait for file to finish writing, then transcribe.
        """
        filename = os.path.basename(file_path)
        
        # Debounce: If processed in last 60 seconds, skip
        if filename in self.last_processed:
            if time.time() - self.last_processed[filename] < 60:
                return
        
        logger.info(f"Detected potential new file: {filename}")
        
        # Wait for file to settle (Camtasia might still be rendering)
        file_size = -1
        stable_count = 0
        while stable_count < 5:
            try:
                current_size = os.path.getsize(file_path)
                if current_size == file_size and current_size > 0:
                    stable_count += 1
                else:
                    stable_count = 0
                    file_size = current_size
                time.sleep(2)
            except OSError:
                time.sleep(2)

        logger.info(f"File stable. Starting AXI Ingestion for: {filename}")
        
        try:
            # --- TRANSCRIBE ---
            # Whisper handles audio extraction from video automatically via ffmpeg
            result = self.model.transcribe(file_path, fp16=torch.cuda.is_available())
            
            transcript_text = result["text"].strip()
            segments = result["segments"] # detailed timestamps
            
            self.save_artifacts(filename, transcript_text, segments)
            
            self.last_processed[filename] = time.time()
            logger.info(f"SUCCESS: Ingested {filename}")

        except Exception as e:
            logger.error(f"FAILED to process {filename}: {e}")

    def save_artifacts(self, filename, text, segments):
        """
        Saves the intelligence in durable formats.
        """
        base_name = os.path.splitext(filename)[0]
        timestamp = datetime.now().isoformat()
        
        # Ensure output dir exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 1. Save Raw Text (Readable)
        txt_path = os.path.join(OUTPUT_DIR, f"{base_name}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"AXI RECORDING: {base_name}\n")
            f.write(f"DATE: {timestamp}\n")
            f.write("-" * 50 + "\n\n")
            f.write(text)
            
        # 2. Save JSON with Timestamps (Training Data)
        json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")
        data = {
            "meta": {
                "source_file": filename,
                "date_ingested": timestamp,
                "axi_type": "oral_history"
            },
            "full_text": text,
            "segments": segments # Contains start/end times for every sentence
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

def main():
    # check for output directories
    if not os.path.exists(WATCH_DIR):
        print(f"WARNING: Watch directory '{WATCH_DIR}' does not exist. Please create it.")
        # os.makedirs(WATCH_DIR) # Uncomment to auto-create
        
    print(f"--- AXI INGESTION ENGINE INITIALIZED ---")
    print(f"Model: Whisper {MODEL_SIZE}")
    print(f"Watching: {WATCH_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Press Ctrl+C to stop.")

    # Load Model (Downloads on first run)
    print("Loading Whisper Model... (this may take a moment)")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Compute Device: {device.upper()}")
    
    model = whisper.load_model(MODEL_SIZE, device=device)
    print("Model Loaded. Listening for videos...")

    event_handler = AXIVideoHandler(model)
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()
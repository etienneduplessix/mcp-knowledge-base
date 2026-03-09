#!/usr/bin/env python3
"""
Simple media processor for knowledge base
Usage: python media_processor.py <file_path> [--contact <name>]
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Check file type
def get_file_info(file_path):
    path = Path(file_path)
    ext = path.suffix.lower()
    
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return 'image', ext
    elif ext in ['.mp3', '.wav', '.m4a', '.ogg']:
        return 'audio', ext
    elif ext in ['.mp4', '.mov', '.avi']:
        return 'video', ext
    elif ext in ['.pdf']:
        return 'document', ext
    else:
        return 'unknown', ext

# OCR for images (requires pytesseract)
def process_image(file_path):
    try:
        import pytesseract
        from PIL import Image
        
        text = pytesseract.image_to_string(Image.open(file_path))
        return {
            "success": True,
            "extracted_text": text.strip(),
            "type": "image"
        }
    except ImportError:
        return {
            "success": False,
            "error": "pytesseract not installed. Run: pip install pytesseract pillow"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Speech-to-text for audio (requires whisper)
def process_audio(file_path):
    try:
        import whisper
        
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        
        return {
            "success": True,
            "transcript": result["text"].strip(),
            "language": result.get("language", "unknown"),
            "type": "audio"
        }
    except ImportError:
        return {
            "success": False,
            "error": "whisper not installed. Run: pip install openai-whisper"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# For video, extract audio then transcribe  
def process_video(file_path):
    return {
        "success": False,
        "note": "Video processing requires ffmpeg. Save extracted audio first, then process as audio."
    }

# Create media metadata
def create_media_record(file_path, result, contact_name=None):
    path = Path(file_path)
    
    record = {
        "type": result.get("type", "unknown"),
        "original_file": str(file_path),
        "filename": path.name,
        "processed_date": datetime.now().isoformat(),
        "size_bytes": path.stat().st_size,
    }
    
    if result.get("extracted_text"):
        record["extracted_text"] = result["extracted_text"]
    
    if result.get("transcript"):
        record["transcript"] = result["transcript"]
        record["language"] = result.get("language", "unknown")
    
    if contact_name:
        record["linked_contact"] = contact_name
    
    return record

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file_path> [--contact <name>]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    contact_name = None
    
    if "--contact" in sys.argv:
        idx = sys.argv.index("--contact")
        if idx + 1 < len(sys.argv):
            contact_name = sys.argv[idx + 1]
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    file_type, ext = get_file_info(file_path)
    
    print(f"Processing {file_type} file: {file_path}")
    
    # Process based on type
    if file_type == 'image':
        result = process_image(file_path)
    elif file_type == 'audio':
        result = process_audio(file_path)
    elif file_type == 'video':
        result = process_video(file_path)
    else:
        print(f"Unsupported file type: {ext}")
        sys.exit(1)
    
    # Show result
    if result.get("success"):
        print("✓ Processing successful!")
        print(f"\nType: {result.get('type')}")
        
        if "extracted_text" in result:
            print(f"\nExtracted text:\n{result['extracted_text'][:500]}...")
        
        if "transcript" in result:
            print(f"\nTranscript:\n{result['transcript'][:500]}...")
        
        # Create record and save
        record = create_media_record(file_path, result, contact_name)
        
        # Save to processed folder
        kb_base = Path.home() / "knowledge-base" / "media" / "processed"
        kb_base.mkdir(parents=True, exist_ok=True)
        
        output_file = kb_base / f"{Path(file_path).stem}.json"
        with open(output_file, 'w') as f:
            json.dump(record, f, indent=2)
        
        print(f"\n✓ Metadata saved to: {output_file}")
        
        if contact_name:
            print(f"✓ Linked to contact: {contact_name}")
            print(f"\nTo complete link:")
            print(f"  mcporter call personal-kb.kb_read_file file_path=\"/Users/etienneduplessix/knowledge-base/people/contacts/{contact_name.lower().replace(' ', '-')}.json\"")
            
    else:
        print(f"✗ Processing failed: {result.get('error')}")

if __name__ == "__main__":
    main()

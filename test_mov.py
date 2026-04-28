#!/usr/bin/env python3
"""
Test script to simulate MOV file processing and diagnose 502 errors.
"""

import sys
import os
import tempfile
import subprocess

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import detect_ffmpeg, transcode_video_to_mp4

def test_mov_transcoding():
    """Test MOV file transcoding with a sample file."""
    print("Testing MOV transcoding...")

    # Check if ffmpeg is available
    ffmpeg_path = detect_ffmpeg()
    if not ffmpeg_path:
        print("ERROR: FFmpeg not available")
        return False

    print(f"OK: FFmpeg available at: {ffmpeg_path}")

    # Create a test MOV file (using ffmpeg to generate one)
    with tempfile.NamedTemporaryFile(suffix=".mov", delete=False) as test_file:
        test_input_path = test_file.name

    try:
        # Generate a test MOV file using ffmpeg
        print(f"Creating test MOV file: {test_input_path}")

        # Create a simple test video with ffmpeg
        cmd = [
            ffmpeg_path,
            "-f", "lavfi",
            "-i", "color=c=red:s=320x240:d=5",
            "-f", "lavfi",
            "-i", "sine=frequency=1000:duration=5",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-y",
            test_input_path
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode != 0:
            print(f"ERROR: Failed to create test MOV file")
            print(f"stderr: {result.stderr.decode('utf-8', errors='replace')}")
            return False

        print(f"OK: Test MOV file created: {os.path.getsize(test_input_path)} bytes")

        # Test transcoding the MOV file
        print(f"Testing transcoding...")

        with open(test_input_path, "rb") as f:
            input_data = f.read()

        try:
            output_data = transcode_video_to_mp4(input_data, max_duration=5)
            print(f"OK: Transcoding successful: {len(output_data)} bytes output")
            return True

        except Exception as e:
            print(f"ERROR: Transcoding failed: {e}")
            return False

    finally:
        # Clean up
        if os.path.exists(test_input_path):
            os.unlink(test_input_path)
            print(f"Cleaned up test file")

if __name__ == "__main__":
    print("MOV Transcoding Test")
    print("=" * 50)

    success = test_mov_transcoding()

    print("=" * 50)
    if success:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Tests failed!")
        sys.exit(1)
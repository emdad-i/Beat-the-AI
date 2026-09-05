"""Test script to exercise the streaming TTS endpoint and print detailed errors.

Run with the project's venv and PYTHONPATH set:
PYTHONPATH=. .venv/bin/python scripts/test_tts_stream.py
"""
import os
import sys
import traceback
from llm.config import client, DEFAULT_TTS_MODEL

def main():
    text = "This is a short connectivity test for streaming TTS."
    print(f"Using model: {DEFAULT_TTS_MODEL}")
    try:
        with client.audio.speech.with_streaming_response.create(
            model=DEFAULT_TTS_MODEL,
            voice="onyx",
            input=text,
            response_format="mp3"
        ) as resp:
            print("Streaming response opened. Reading bytes...")
            count = 0
            for chunk in resp.iter_bytes(chunk_size=65536):
                count += 1
                print(f"Received chunk {count}, {len(chunk)} bytes")
            print(f"Streaming finished, {count} chunks received.")
    except Exception as e:
        print("STREAMING ERROR:", type(e).__name__, e)
        traceback.print_exc()
        # Try a quick non-streaming call for comparison
        try:
            print("Attempting non-streaming fallback...")
            fallback = client.audio.speech.create(
                model=DEFAULT_TTS_MODEL,
                voice="onyx",
                input=text,
                response_format="mp3"
            )
            # Try to detect bytes
            if hasattr(fallback, 'iter_bytes'):
                print("Fallback returned iterable bytes")
            elif hasattr(fallback, 'content'):
                print(f"Fallback returned content of length: {len(fallback.content)}")
            else:
                print("Fallback returned object:", type(fallback))
        except Exception as e2:
            print("FALLBACK ERROR:", type(e2).__name__, e2)
            traceback.print_exc()

if __name__ == '__main__':
    main()

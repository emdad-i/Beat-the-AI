#!/usr/bin/env python3
"""Quick script to list available TTS-capable models for the configured OpenAI client."""
from llm.config import get_available_tts_models, KNOWN_TTS_MODELS, DEFAULT_TTS_MODEL

if __name__ == '__main__':
    print("Known TTS model candidates:")
    for m in KNOWN_TTS_MODELS:
        print(f" - {m}")

    available = get_available_tts_models()
    if available:
        print("\nAvailable on your account:")
        for m in available:
            print(f" - {m}")
    else:
        print("\nNo known TTS models detected via the API. You may still have access to other models or the API call failed.")

    print(f"\nConfigured default TTS model: {DEFAULT_TTS_MODEL}")

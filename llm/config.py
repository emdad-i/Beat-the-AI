import os
from openai import OpenAI

# Centralized OpenAI client construction.
# Import `client` from this module in other parts of the app.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Default models can be configured here for easy maintenance
DEFAULT_CHAT_MODEL = "gpt-4o"
DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"

# Known TTS-capable model ids to check against the API. Keep this list updated as OpenAI adds/removes models.
KNOWN_TTS_MODELS = [
	"tts-1",
	"tts-1-hd",
	"gpt-4o-mini-tts",
	"gpt-4o-mini-tts-2025-12-15",
]


def get_available_tts_models():
	"""Query the OpenAI API for available models and return any that match KNOWN_TTS_MODELS.

	Returns a list of model ids present in the account that are known to support TTS.
	"""
	try:
		resp = client.models.list()
		ids = [m.id for m in resp.data]
		available = [m for m in KNOWN_TTS_MODELS if m in ids]
		return available
	except Exception:
		return []

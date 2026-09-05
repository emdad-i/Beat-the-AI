# 🎭 FSOCIETY: BEAT THE AI
### A Mr. Robot Inspired Debate Workshop & Game

This is a Flask-based interactive game where two teams ("Nodes") compete in a battle of logic and ethics judged by `gpt-5.6-luna`. The system features a TV Broadcast interface with real-time audio, a time pressure, and a mobile portal for player submissions.

---

## 🛠️ Prerequisites

* **uv** installed (`brew install uv` on macOS).
* **OpenAI API Key** with access to the configured chat and TTS models.
* All devices (Laptop and Phones) must be on the **same Wi-Fi network**.

---

## 🚀 Developer Quick Start

### 1. Clone and enter the project
```bash
git clone https://github.com/emdad-i/Beat-the-AI.git
cd Beat-the-AI
```

### 2. Create the uv environment
```bash
uv sync
```

### 3. Set the API key for this terminal
```bash
export OPENAI_API_KEY='your-api-key'
```

Windows PowerShell:  
```powershell
$env:OPENAI_API_KEY="your-key-here"
```

---

## 🏃 Running the Game

### 1. Start the Server  
```bash
uv run python app.py
```

Open `http://localhost:5001/tv` on the display and `http://YOUR_LOCAL_IP:5001` on player devices. Keep the API key out of source control.

### 2. Open the Interfaces  
* TV Screen (Projector): http:localhost:5001/tv  
* Player Portal (Phones): http:YOUR_LOCAL_IP:5001

---

## 🎮 How to Play

* **BOOT SYSTEM:** Click the red "RUN BOOT SECTOR" button on the TV.  
* **REGISTRATION:** Teams join via phones. When both are online, click **Start Game**.  
* **THE ROUND:** Click **BROADCAST Q** to hear the AI prompt and start the 60s timer. Teams discuss and submit via phones.  
* **THE JUDGMENT:** Click **AI VERDICT** to hear the AI compare arguments and award points.  
* **SYSTEM RESET:** Hover top-right corner on TV to reveal the hidden reset button.

---

## 🤖 AI Models

The current model configuration is:

* **Chat and verdicts:** `gpt-5.6-luna`
* **Text-to-speech:** `gpt-4o-mini-tts`

These defaults are defined in `llm/config.py`.

## 📦 Dependencies

Dependencies are managed in `pyproject.toml` and pinned in `uv.lock`.

---

## 📦 requirements.txt  
Dependencies are declared in `pyproject.toml` and locked in `uv.lock`.

## 🗂️ Project Structure

The LLM-related configuration and prompts have been moved into a dedicated package for easier maintenance:

- `llm/config.py`: OpenAI client and model defaults
- `llm/prompts.py`: Question list and prompt-builder helpers

This makes it easier to update prompts or swap models without changing `app.py`.

### Checking available TTS models

You can check which known TTS models your OpenAI account can access:

```bash
uv run python scripts/check_tts_models.py
```

If streaming still fails, try `tts-1-hd` or one of the `gpt-4o-mini-tts` variants if they appear in the list.

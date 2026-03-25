# 🎭 FSOCIETY: BEAT THE AI
### A Mr. Robot Inspired Debate Workshop & Game

This is a Flask-based interactive game where two teams ("Nodes") compete in a battle of logic and ethics judged by GPT-4o. The system features a TV Broadcast interface with real-time audio, a 60-second pressure timer, and a mobile portal for player submissions.

---

## 🛠️ Prerequisites

* **Python 3.8+** installed.  
* **OpenAI API Key** with access to GPT-4o and TTS-1.  
* All devices (Laptop and Phones) must be on the **same Wi-Fi network**.

---

## 🚀 Installation & Setup

### 1. Navigate to Project Folder  
```bash
cd Beat-the-AI
```

### 2. Install Dependencies  
```bash
pip install -r requirements.txt
```

### 3. Set Environment Variable  
```bash
export OPENAI_API_KEY='sk-proj-your-actual-key-here'
```

Windows PowerShell:  
```powershell
$env:OPENAI_API_KEY="your-key-here"
```

---

## 🏃 Running the Game

### 1. Start the Server  
```bash
python app.py
```

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

## 📦 Dependencies

* Flask & Flask-SocketIO  
* OpenAI (GPT-4o & Onyx TTS)  
* Eventlet  

---

## 📦 requirements.txt  
```text
flask
flask-socketio
openai
eventlet
python-dotenv
```

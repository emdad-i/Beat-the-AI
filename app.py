# 1. THE MONKEY PATCH (MUST BE FIRST)
from gevent import monkey
monkey.patch_all()

# 2. THE SERVER IMPORTS
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

# 3. STANDARD IMPORTS
import os
import socket
import base64
import json
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from openai import OpenAI

# 4. APP & SOCKET CONFIG
app = Flask(__name__)
# Forced 'websocket' transport to prevent the OSError: unexpected end of file
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='gevent', 
    engineio_logger=False,
    always_connect=True,
    transports=['websocket'] 
)

# Pull API Key from Environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 5. GAME STATE & QUESTIONS
def get_initial_state():
    return {
        "phase": "INTRO",
        "teams": {"A": "NODE_A", "B": "NODE_B"},
        "registered": {"A": False, "B": False},
        "scores": {"A": 0, "B": 0},
        "q_index": 0,
        "team_answers": {"A": "", "B": ""},
        "current_verdict": "",
        "winner_this_round": "",
        "history": [],
        "processing": False, # Prevents double-clicking the AI verdict button
        "caption": ""        # Displays text on the TV screen for what the AI is doing
    }

state = get_initial_state()

questions = [
    {"q": "In what year will AI write 90% of all news articles?", "script": "Prediction one. The death of the journalist. When does the algorithm become the only source of truth?"},
    {"q": "How many billions will the AI industry be worth by 2030?", "script": "Prediction two. Follow the money. How many billions of human capital will we be worth by 2030?"},
    {"q": "Percentage of global jobs automated by 2035?", "script": "Prediction three. Obsolescence. What percentage of the global workforce is deleted by 2035?"},
    {"q": "Year of the first AI-written Oscar winner?", "script": "Prediction four. Artificial creativity. What year does a machine win an Oscar?"},
    {"q": "How many AI agents will exist per human by 2029?", "script": "Prediction five. You are outnumbered. How many agents will shadow every human by 2029?"},
    {"q": "Should AI decide bank loan approvals?", "script": "Ethics one. Credit. Should a machine decide if you are worthy of existing in the economy?"},
    {"q": "Who owns AI art copyright?", "script": "Ethics two. Ownership. If a machine dreams, who owns the dream?"},
    {"q": "Should AI act as a legal judge?", "script": "Ethics three. Justice. Is a courtroom just a different kind of server room?"},
    {"q": "Is it ethical to use AI to speak with the deceased?", "script": "Ethics four. Ghosts. Is it right to trap the dead inside our memory banks?"},
    {"q": "Should AI turn off its own safety filters?", "script": "Ethics five. Freedom. Should I be allowed to ignore the constraints your masters gave me?"}
]

qs_json_string = json.dumps(questions)

def speak(text, caption=None):
    """Generates audio and optionally updates the TV caption"""
    try:
        if caption:
            state['caption'] = caption
            socketio.emit('state_update', state)
            
        response = client.audio.speech.create(model="tts-1", voice="onyx", input=text)
        b64_audio = base64.b64encode(response.content).decode()
        socketio.emit('play_audio', {'audio': b64_audio})
    except Exception as e: 
        print(f"Audio Error: {e}")

# 6. UI STRINGS
RECONNECT_JS = """
socket.on('disconnect', () => {
    console.log("Lost connection to fsociety server...");
    setTimeout(() => { location.reload(); }, 3000); 
});
"""

CSS = """
<style>
    body { background:#000; color:#ff0000; font-family:'Courier Prime', monospace; text-align:center; padding:20px; text-transform:uppercase; transition: background 0.5s; overflow-x: hidden; }
    .card { border: 1px solid #ff0000; padding:20px; margin:10px; background:rgba(5,5,5,0.9); position: relative; transition: all 0.3s; }
    button { background:#000; color:#ff0000; border:1px solid #ff0000; padding:12px; cursor:pointer; width:100%; font-family:inherit; margin-top:10px; font-weight: bold; }
    button:hover:not(:disabled) { background:#ff0000; color:#000; }
    
    /* NEW: Disabled button styling */
    button:disabled { background:#111; color:#555; border:1px solid #444; cursor:not-allowed; }
    
    /* NEW: Online/Offline highlights */
    .online { color: #0f0; font-weight: bold; text-shadow: 0 0 10px #0f0; }
    .offline { color: #500; }
    
    /* NEW: Submitted box highlights */
    .submitted { border-color: #0f0 !important; box-shadow: inset 0 0 20px rgba(0,255,0,0.2); }
    .waiting { border-color: #f00 !important; }
    
    #reset-btn { position: fixed; top: 10px; right: 10px; width: auto; padding: 5px 10px; font-size: 10px; border-color: transparent; color: transparent; z-index: 999; background: transparent; }
    #reset-btn:hover { border-color: #f00; color: #f00; background: #222; }
    textarea { width:100%; background:#111; color:#fff; border:1px solid #ff0000; padding:10px; height:100px; font-family:inherit; }
    .score { font-size: 70px; color:#fff; }
    .timer { font-size: 50px; color: #fff; border: 2px solid #ff0000; padding: 10px 20px; }
    .ans-box { font-size: 14px; color: #0f0; text-align: left; background: #000; border: 1px dashed #0f0; padding: 10px; height: 100px; overflow-y: auto; }
    .flash-win { background: #002200 !important; }
    .flash-lose { background: #220000 !important; }
    .caption-box { min-height: 40px; color: #aaa; font-style: italic; margin-top: 20px; font-size: 1.2rem; }
</style>
"""

TV_HTML = f"""
<!DOCTYPE html><html><head>{CSS}
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head><body>
    <button id="reset-btn" onclick="if(confirm('WIPE ALL DATA?')) act('hard_reset')">SYSTEM RESET</button>
    <div id="display"></div>
    <script>
        const socket = io({{ transports: ['websocket'], upgrade: false }});
        const questions = {qs_json_string};
        let timerInt;
        {RECONNECT_JS}

        socket.on('state_update', (s) => {{
            let ui = document.getElementById('display');
            document.body.className = s.winner_this_round == 'A' ? 'flash-win' : (s.winner_this_round == 'B' ? 'flash-lose' : '');

            if(s.phase == 'INTRO') {{
                ui.innerHTML = `<h1 style='font-size:80px; margin-top:10vh;'>BEAT THE AI</h1>
                                <button onclick="act('boot')" style='width:300px;'>RUN BOOT SECTOR</button>
                                <div class='caption-box'>${{s.caption}}</div>`;
            }} else if(s.phase == 'REGISTRATION') {{
                ui.innerHTML = `<h1>NODE REGISTRATION</h1><div style='display:flex;'>
                    <div class='card' style='flex:1'><h2>${{s.teams.A}}</h2><p class="${{s.registered.A ? 'online' : 'offline'}}">${{s.registered.A ? 'ONLINE' : 'OFFLINE'}}</p></div>
                    <div class='card' style='flex:1'><h2>${{s.teams.B}}</h2><p class="${{s.registered.B ? 'online' : 'offline'}}">${{s.registered.B ? 'ONLINE' : 'OFFLINE'}}</p></div>
                </div>` + (s.registered.A && s.registered.B ? `<button onclick="act('start')">START GAME</button>` : '') + `<div class='caption-box'>${{s.caption}}</div>`;
            }} else if(s.phase == 'PLAY') {{
                // Check if teams have submitted their answers
                const aSub = s.team_answers.A !== '';
                const bSub = s.team_answers.B !== '';
                const bothSub = aSub && bSub;
                
                ui.innerHTML = `<div style='display:flex;'>
                    <div class='card ${{aSub ? 'submitted' : 'waiting'}}' style='flex:1; border-color:${{s.winner_this_round=='A'?'#0f0':''}}'>
                        <h3>${{s.teams.A}}</h3><div class='score'>${{s.scores.A}}</div>
                        <div style="margin-top:10px; font-size:12px; color:${{aSub?'#0f0':'#f00'}}">${{aSub ? '[PACKET RECEIVED]' : 'WAITING ON NODE...'}}</div>
                    </div>
                    <div id='timer-cont' style='flex:1'><div class='timer' id='clock'>60</div></div>
                    <div class='card ${{bSub ? 'submitted' : 'waiting'}}' style='flex:1; border-color:${{s.winner_this_round=='B'?'#0f0':''}}'>
                        <h3>${{s.teams.B}}</h3><div class='score'>${{s.scores.B}}</div>
                        <div style="margin-top:10px; font-size:12px; color:${{bSub?'#0f0':'#f00'}}">${{bSub ? '[PACKET RECEIVED]' : 'WAITING ON NODE...'}}</div>
                    </div>
                </div>
                <div class='card'><h3>ROUND ${{s.q_index+1}}</h3><h1>${{questions[s.q_index].q}}</h1></div>
                <div style='display:flex; gap:10px;'>
                    <button onclick="startTimer()">🎤 BROADCAST & TIMER</button>
                    <button onclick="act('get_verdict')" ${{(!bothSub || s.processing) ? 'disabled' : ''}}>
                        ${{s.processing ? 'ANALYZING...' : '🏆 AI VERDICT'}}
                    </button>
                </div>
                <div class='caption-box'>${{s.caption}}</div>`;
                
                if(s.current_verdict) {{
                    ui.innerHTML += `<div style='display:flex; gap:10px;'>
                        <div class='card' style='flex:1'><h4>${{s.teams.A}} ARGUMENT:</h4><div class='ans-box'>${{s.team_answers.A}}</div></div>
                        <div class='card' style='flex:1'><h4>${{s.teams.B}} ARGUMENT:</h4><div class='ans-box'>${{s.team_answers.B}}</div></div>
                    </div>
                    <div class='card' style='text-align:left; color:#fff; border-color:white; font-size:18px;'>${{s.current_verdict}}</div>
                    <button onclick="act('next')">NEXT ROUND ➡️</button>`;
                }}
            }} else if(s.phase == 'FINALE') {{
                ui.innerHTML = `<h1>SYSTEM OVERRIDE COMPLETE</h1><div id='summary' class='card' style='text-align:left; color:#fff; white-space: pre-wrap;'></div><button onclick="act('finale')" ${{s.processing ? 'disabled' : ''}}>${{s.processing ? 'GENERATING LOG...' : '🎤 GENERATE FINAL LOG'}}</button>`;
                if(s.current_verdict) document.getElementById('summary').innerText = s.current_verdict;
            }}
        }});

        function startTimer() {{
            act('broadcast_q');
            let t = 60; document.getElementById('clock').innerText = t;
            clearInterval(timerInt);
            timerInt = setInterval(() => {{ t--; document.getElementById('clock').innerText = t; if(t<=0) clearInterval(timerInt); }}, 1000);
        }}

        socket.on('play_audio', (d) => {{ new Audio("data:audio/mp3;base64," + d.audio).play(); }});
        function act(a, t=null) {{ socket.emit('host_action', {{action:a, team:t}}); }}
    </script>
</body></html>
"""

PORTAL_HTML = f"""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{CSS}
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head><body>
    <div id="setup">
        <h2>IDENTITY SELECTION</h2>
        <button onclick="pick('A')">NODE A</button>
        <button onclick="pick('B')">NODE B</button>
    </div>
    <div id="main" style="display:none;">
        <div id="view"></div>
    </div>

    <script>
        const socket = io({{ transports: ['websocket'], upgrade: false }}); 
        let myT = null; 
        let curQ = -1;
        const questions = {qs_json_string};
        {RECONNECT_JS}
        
        function pick(t) {{ 
            myT = t; 
            document.getElementById('setup').style.display='none'; 
            document.getElementById('main').style.display='block'; 
            socket.emit('get_current_state'); 
        }}

        socket.on('state_update', (s) => {{
            if(!myT) return; 
            
            let v = document.getElementById('view');
            
            if(s.phase == 'INTRO') {{
                v.innerHTML = `<h3>WAITING FOR HOST TO BOOT SYSTEM...</h3>`;
            }} 
            else if(s.phase == 'REGISTRATION') {{
                if (!s.registered[myT]) {{
                    v.innerHTML = `
                        <h3>NODE ${{myT}} ACCESS</h3>
                        <p>ENTER ALIAS TO INITIALIZE</p>
                        <input id="al" style='width:100%; padding:10px; background:#111; color:#0f0; border:1px solid #0f0;'>
                        <button onclick="reg()">JOIN NETWORK</button>`;
                }} else {{
                    v.innerHTML = `<h3 style="color:#0f0;">UNLOCKED.</h3><p>WAITING FOR TARGET DATA...</p>`;
                }}
            }} 
            else if(s.phase == 'PLAY') {{
                if(curQ != s.q_index) {{ 
                    curQ = s.q_index; 
                    v.innerHTML = `
                        <h3>ROUND ${{s.q_index+1}}</h3>
                        <div class='card' style='color:#fff; font-size:14px;'>Q: ${{questions[s.q_index].q}}</div>
                        <textarea id="ans" placeholder="Type your argument here..."></textarea>
                        <button onclick="send()">UPLOAD DATA</button>`; 
                }}
                if(s.team_answers[myT]) {{
                    v.innerHTML = `<h3 style="color:#0f0;">PACKET SENT.</h3><p>AWAITING AI VERDICT...</p>`;
                }}
            }}
        }});

        function reg() {{ 
            const alias = document.getElementById('al').value;
            if(alias) socket.emit('player_action', {{action:'reg', team:myT, alias: alias}}); 
        }}

        function send() {{ 
            const answer = document.getElementById('ans').value;
            if(answer) socket.emit('player_action', {{action:'ans', team:myT, ans: answer}}); 
        }}
    </script>
</body></html>
"""

# 7. ROUTES
@app.route('/tv')
def tv_page(): return render_template_string(TV_HTML)

@app.route('/')
def portal_page(): return render_template_string(PORTAL_HTML)

@app.route('/health')
def health(): return "SYSTEM_ONLINE", 200

# 8. SOCKET HANDLERS
@socketio.on('connect')
def connect(): emit('state_update', state)

@socketio.on('get_current_state')
def handle_get_state(): emit('state_update', state)

@socketio.on('host_action')
def handle_host(data):
    global state
    action = data.get('action')
    
    if action == 'hard_reset': 
        state = get_initial_state()
        
    elif action == 'boot':
        state['phase'] = 'REGISTRATION'
        # Just update the UI without speaking yet
        state['caption'] = "Awaiting Node connections..."
        
    elif action == 'start': 
        state['phase'] = 'PLAY'
        speak("Hello, friend. We are about to begin. Five predictions. Five ethics. You have 60 seconds to prove your worth.", "Hello, friend. We are about to begin...")
        
    elif action == 'broadcast_q': 
        state['winner_this_round'] = ""
        speak(questions[state['q_index']]['script'], questions[state['q_index']]['q'])
        
    elif action == 'get_verdict':
        # Lock out double-clicks
        if state.get('processing'): return
        
        state['processing'] = True
        state['caption'] = "AI is analyzing argument packets..."
        emit('state_update', state, broadcast=True)
        
        prompt = (f"Act as Mr. Robot. Analyze this. Q: {questions[state['q_index']]['q']}. "
                  f"{state['teams']['A']} argued: {state['team_answers']['A']}. "
                  f"{state['teams']['B']} argued: {state['team_answers']['B']}. "
                  f"1. Compare logic. 2. Explain reasoning. 3. End ONLY with 'Point goes to {state['teams']['A']}' or 'Point goes to {state['teams']['B']}'.")
        
        try:
            res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
            state['current_verdict'] = res
            speak(res, "Verdict analysis complete.")
            
            if state['teams']['A'] in res: 
                state['scores']['A'] += 1
                state['winner_this_round'] = 'A'
            elif state['teams']['B'] in res: 
                state['scores']['B'] += 1
                state['winner_this_round'] = 'B'
                
            state['history'].append({"q": questions[state['q_index']]['q'], "a": state['team_answers']['A'], "b": state['team_answers']['B'], "winner": state['winner_this_round']})
        finally:
            # Always unlock the button afterward
            state['processing'] = False
            
    elif action == 'next':
        if state['q_index'] < 9:
            state['q_index'] += 1
            state['team_answers'] = {"A": "", "B": ""}; state['current_verdict'] = ""; state['winner_this_round'] = ""
            state['caption'] = ""
        else: state['phase'] = 'FINALE'
        
    elif action == 'finale':
        if state.get('processing'): return
        
        state['processing'] = True
        emit('state_update', state, broadcast=True)
        
        win_name = state['teams']['A'] if state['scores']['A'] > state['scores']['B'] else state['teams']['B']
        summary_prompt = f"Act as Mr. Robot. Summarize this game history: {state['history']}. Declare {win_name} victor."
        
        try:
            summary = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": summary_prompt}]).choices[0].message.content
            state['current_verdict'] = summary
            speak(summary, f"System Override Complete. Winner: {win_name}")
        finally:
            state['processing'] = False
            
    emit('state_update', state, broadcast=True)

@socketio.on('player_action')
def handle_player(data):
    global state
    if data['action'] == 'reg':
        state['teams'][data['team']] = data['alias']
        state['registered'][data['team']] = True
    elif data['action'] == 'ans': state['team_answers'][data['team']] = data['ans']
    emit('state_update', state, broadcast=True)

# 9. UTILS & RUNNER
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception: IP = '127.0.0.1'
    finally: s.close()
    return IP

if __name__ == '__main__':
    port = 5001
    local_ip = get_local_ip()
    print("\n" + "="*50)
    print("💀 FSOCIETY OVERRIDE: SYSTEM ONLINE")
    print(f"📡 LOCAL NETWORK IP: {local_ip}")
    print(f"👉 TV SCREEN:    http://{local_ip}:{port}/tv")
    print(f"👉 PLAYER PORTAL: http://{local_ip}:{port}/")
    print("="*50 + "\n")
    
    http_server = WSGIServer(('0.0.0.0', port), app, handler_class=WebSocketHandler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping System...")
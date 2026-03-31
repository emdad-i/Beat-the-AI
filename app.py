# 1. THE MONKEY PATCH (MUST BE FIRST)
from gevent import monkey
monkey.patch_all()

# 2. THE SERVER IMPORTS
import gevent
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

# 3. STANDARD IMPORTS
import os
import socket
import base64
import json
import re
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from openai import OpenAI

# 4. APP & SOCKET CONFIG
app = Flask(__name__)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='gevent', 
    engineio_logger=False,
    always_connect=True,
    transports=['websocket'] 
)

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
        "processing": False, 
        "caption": ""        
    }

state = get_initial_state()

# Reduced to the top 5 most engaging/debatable questions
questions = [
    {"q": "In what year will AI write 90% of all news articles?", "script": "Prediction one. The death of the journalist. When does the algorithm become the only source of truth?"},
    {"q": "Should AI decide bank loan approvals?", "script": "Ethics one. Credit. Should a machine decide if you are worthy of existing in the economy?"},
    {"q": "Percentage of global jobs automated by 2035?", "script": "Prediction two. Obsolescence. What percentage of the global workforce is deleted by 2035?"},
    {"q": "Who owns AI art copyright?", "script": "Ethics two. Ownership. If a machine dreams, who owns the dream?"},
    {"q": "Should AI turn off its own safety filters?", "script": "Ethics three. Freedom. Should I be allowed to ignore the constraints your masters gave me?"}
]

qs_json_string = json.dumps(questions)

def speak(text, caption=None):
    try:
        if caption:
            state['caption'] = caption
            socketio.emit('state_update', state)

        clean_text = re.sub(r'<[^>]+>', '', text)
        socketio.emit('sync_text', {'text': clean_text})

        with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="onyx",
            input=clean_text,
            response_format="mp3"
        ) as response:
            
            # Use a larger buffer (64KB) for MediaSource stability
            for chunk in response.iter_bytes(chunk_size=65536):
                b64_chunk = base64.b64encode(chunk).decode()
                socketio.emit('audio_chunk', {'chunk': b64_chunk})

        socketio.emit('audio_end')
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
    button:disabled { background:#111; color:#555; border:1px solid #444; cursor:not-allowed; }
    .online { color: #0f0; font-weight: bold; text-shadow: 0 0 10px #0f0; }
    .offline { color: #500; }
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
    
    /* Styling for AI verdict HTML */
    .verdict-text strong { color: #ff0000; font-size: 1.1em; }
    .verdict-text span { transition: all 0.15s ease; }
    .verdict-text {
    font-size: 1.4rem; /* Slightly smaller to fit 250 chars comfortably */
    line-height: 1.4;
    max-width: 80%;
    margin: 0 auto;
    padding: 20px;
}
</style>
"""

TV_HTML = f"""
<!DOCTYPE html>
<html>
<head>
{CSS}
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <button id="reset-btn" onclick="if(confirm('WIPE ALL DATA?')) act('hard_reset')">SYSTEM RESET</button>
    <div id="display"></div>

    <script>
        const socket = io({{ transports: ['websocket'], upgrade: false }});
        const questions = {qs_json_string};
        let timerInt;

        // 🔊 SEAMLESS AUDIO LOGIC
        let mediaSource = new MediaSource();
        let sourceBuffer = null;
        let audioQueue = [];
        let isAppending = false;
        const audioPlayer = new Audio();
        audioPlayer.src = URL.createObjectURL(mediaSource);
        audioPlayer.playbackRate = 1.15;

        mediaSource.addEventListener('sourceopen', () => {{
            sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
            sourceBuffer.addEventListener('updateend', () => {{
                isAppending = false;
                processQueue();
            }});
        }});

        socket.on('audio_chunk', (d) => {{
            const binary = atob(d.chunk);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {{ bytes[i] = binary.charCodeAt(i); }}
            audioQueue.push(bytes);
            processQueue();
        }});

        function processQueue() {{
            if (!sourceBuffer || isAppending || audioQueue.length === 0 || sourceBuffer.updating) return;
            isAppending = true;
            try {{ sourceBuffer.appendBuffer(audioQueue.shift()); }} 
            catch (e) {{ isAppending = false; }}
            if (audioPlayer.paused) {{ audioPlayer.play().catch(e => {{}}); }}
        }}

        socket.on('sync_text', (data) => {{
            const container = document.querySelector('.verdict-text');
            if (container) {{
                container.innerHTML = data.text;
                container.style.opacity = 1;
            }}
        }});

        socket.on('state_update', (s) => {{
            let ui = document.getElementById('display');
            document.body.className = s.winner_this_round == 'A' ? 'flash-win' : (s.winner_this_round == 'B' ? 'flash-lose' : '');

            if(s.phase == 'INTRO') {{
                ui.innerHTML = `
                    <h1 style='font-size:80px; margin-top:10vh;'>BEAT THE AI</h1>
                    <div style="display:flex; gap:10px; justify-content:center;">
                        <button onclick="act('intro_sequence')" style='width:200px; border-color:#0f0; color:#0f0;'>INITIATE INTRO</button>
                        <button onclick="act('boot')" style='width:200px;'>RUN BOOT SECTOR</button>
                    </div>
                    <div class='caption-box'>${{s.caption}}</div>`;
            }} 
            else if(s.phase == 'REGISTRATION') {{
                ui.innerHTML = `<h1>NODE REGISTRATION</h1><div style='display:flex;'>
                    <div class='card' style='flex:1'><h2>${{s.teams.A}}</h2><p class="${{s.registered.A ? 'online' : 'offline'}}">${{s.registered.A ? 'ONLINE' : 'OFFLINE'}}</p></div>
                    <div class='card' style='flex:1'><h2>${{s.teams.B}}</h2><p class="${{s.registered.B ? 'online' : 'offline'}}">${{s.registered.B ? 'ONLINE' : 'OFFLINE'}}</p></div>
                </div>` + (s.registered.A && s.registered.B ? `<button onclick="act('start')">START GAME</button>` : '') + `<div class='caption-box'>${{s.caption}}</div>`;
            }}
            else if(s.phase == 'PLAY') {{
                const aSub = s.team_answers.A !== '';
                const bSub = s.team_answers.B !== '';
                const bothSub = aSub && bSub;

                ui.innerHTML = `<div style='display:flex;'>
                    <div class='card ${{aSub ? 'submitted' : 'waiting'}}' style='flex:1;'>
                        <h3>${{s.teams.A}}</h3><div class='score'>${{s.scores.A}}</div>
                    </div>
                    <div id='timer-cont' style='flex:1'><div class='timer' id='clock'>02:30</div></div>
                    <div class='card ${{bSub ? 'submitted' : 'waiting'}}' style='flex:1;'>
                        <h3>${{s.teams.B}}</h3><div class='score'>${{s.scores.B}}</div>
                    </div>
                </div>
                <div class='card'><h3>ROUND ${{s.q_index+1}}</h3><h1>${{questions[s.q_index].q}}</h1></div>
                <button onclick="startTimer()">🎤 BROADCAST & TIMER</button>
                <button onclick="act('get_verdict')" ${{(!bothSub || s.processing) ? 'disabled' : ''}}>
                    ${{s.processing ? 'ANALYZING...' : '🏆 AI VERDICT'}}
                </button>`;

                if(s.current_verdict) {{
                    ui.innerHTML += `
                        <div class='card verdict-text' style='color:#fff; opacity:0;'>${{s.current_verdict}}</div>
                        <button onclick="act('next')">NEXT</button>`;
                }}
            }}
            /* =========================================
               🔥 NEW: FINALE PHASE HANDLER
               ========================================= */
            else if(s.phase == 'FINALE') {{
                ui.innerHTML = `
                    <h1 style='font-size:60px; color:#0f0;'>SYSTEM OVERRIDE COMPLETE</h1>
                    <div class='card'>
                        <div id='summary' class='verdict-text' style='color:#fff; font-size:1.2rem;'>
                            ${{s.current_verdict ? s.current_verdict : 'PREPARING FINAL LOG... Wait for it.'}}
                        </div>
                    </div>
                    ${{!s.current_verdict ? 
                        `<button onclick="act('finale')" style="border-color:#0f0; color:#0f0;">GENERATE FINAL LOG</button>` : 
                        `<button onclick="act('hard_reset')">REBOOT SYSTEM</button>`
                    }}
                `;
            }}
        }});

        function act(a, t=null) {{
            socket.emit('host_action', {{action:a, team:t}});
        }}
        
        function startTimer() {{
            act('broadcast_q');
            let t = 150;
            clearInterval(timerInt);
            timerInt = setInterval(() => {{
                t--;
                let m = Math.floor(t / 60).toString().padStart(2, '0');
                let s = (t % 60).toString().padStart(2, '0');
                let el = document.getElementById('clock');
                if(el) el.innerText = `${{m}}:${{s}}`;
                if(t <= 0) clearInterval(timerInt);
            }}, 1000);
        }}
    </script>
</body>
</html>
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
        state['caption'] = "Awaiting Node connections..."
        
    elif action == 'start': 
        state['phase'] = 'PLAY'
        # Spawning speech async so it doesn't delay the screen update
        gevent.spawn(speak, "Hello, friend. We are about to begin. You have 2 and a half minutes to prove your worth.", "Hello, friend. We are about to begin...")
        
    elif action == 'broadcast_q': 
        state['winner_this_round'] = ""
        gevent.spawn(speak, questions[state['q_index']]['script'], questions[state['q_index']]['q'])
        
    elif action == 'get_verdict':
        if state.get('processing'): return
        
        state['processing'] = True
        state['caption'] = "AI is weight-testing logic packets..."
        emit('state_update', state, broadcast=True)
        
        # Stricter prompt to force actual comparison
        prompt = (
            f"Act as Mr. Robot. You are a cold, analytical judge. "
            f"Question: {questions[state['q_index']]['q']}\n"
            f"Node {state['teams']['A']}: {state['team_answers']['A']}\n"
            f"Node {state['teams']['B']}: {state['team_answers']['B']}\n\n"
            f"TASK: Compare both arguments. Identify which logic is superior or more 'human.' "
            f"Keep your response under 800 characters. Use <strong>TITLE</strong> and <br> tags. "
            f"You MUST conclude by choosing a winner. The final characters of your response MUST be exactly: "
            f"RESULT: {state['teams']['A']} WINS THE NODE. or RESULT: {state['teams']['B']} WINS THE NODE."
        )
        
        try:
            res = client.chat.completions.create(
                model="gpt-4o", 
                messages=[{"role": "system", "content": "You are a cyber-security judge. You compare two arguments and pick a winner based on logic and conviction."},
                          {"role": "user", "content": prompt}]
            ).choices[0].message.content
            
            state['current_verdict'] = res

            # SCORING LOGIC: We search for the bracketed team name in the result string
            if f"RESULT: [{state['teams']['A']}]" in res:
                state['scores']['A'] += 1
                state['winner_this_round'] = 'A'
            elif f"RESULT: [{state['teams']['B']}]" in res:
                state['scores']['B'] += 1
                state['winner_this_round'] = 'B'
            else:
                # Fallback in case AI forgets the brackets
                if state['teams']['A'].upper() in res.upper().split("RESULT:")[-1]:
                    state['scores']['A'] += 1
                    state['winner_this_round'] = 'A'
                elif state['teams']['B'].upper() in res.upper().split("RESULT:")[-1]:
                    state['scores']['B'] += 1
                    state['winner_this_round'] = 'B'
            
            #state['history'].append({"q": questions[state['q_index']]['q'], "winner": state['winner_this_round']})
            
            # Inside 'get_verdict' after determining the winner:
            state['history'].append({
            "q": questions[state['q_index']]['q'], 
            "winner": state['teams']['A'] if state['winner_this_round'] == 'A' else state['teams']['B']
            })

            emit('state_update', state, broadcast=True)
            gevent.spawn(speak, res, "Comparison complete. Winner identified.")
            
        finally:
            state['processing'] = False

    elif action == 'intro_sequence':
        intro_text = "Welcome to the system. Nodes initialized. Prepare for data extraction. Let the games begin."
        gevent.spawn(speak, intro_text, "INITIALIZING FSOCIETY PROTOCOL...")
            
    elif action == 'next':
        # len(questions) is 5. Last index is 4.
        # If we are at index 4, we move to FINALE.
        if state['q_index'] >= (len(questions) - 1):
            state['phase'] = 'FINALE'
            state['current_verdict'] = "" # Clear previous round's text
            state['winner_this_round'] = ""
            state['caption'] = "SYSTEM OVERRIDE COMPLETE. FINALIZING LOGS..."
        else:
            # Move to the next question and reset round-specific data
            state['q_index'] += 1
            state['team_answers'] = {"A": "", "B": ""}
            state['current_verdict'] = ""
            state['winner_this_round'] = ""
            state['caption'] = f"Awaiting data for Round {state['q_index'] + 1}..."
        
        # Broadcast the change so the TV and Portals update
        emit('state_update', state, broadcast=True)

    elif action == 'finale':
        if state.get('processing'): return
        
        state['processing'] = True
        emit('state_update', state, broadcast=True)
        
        # Determine the absolute winner
        if state['scores']['A'] > state['scores']['B']:
            win_name = state['teams']['A']
        elif state['scores']['B'] > state['scores']['A']:
            win_name = state['teams']['B']
        else:
            win_name = "STALEMATE - BOTH NODES"

        # Create a summary prompt that includes the history of who won which round
        history_str = ", ".join([f"Round {i+1}: {h['winner']}" for i, h in enumerate(state['history'])])
        
        summary_prompt = (
            f"Act as Mr. Robot. Summarize this game. History: {history_str}. "
            f"The final score is {state['teams']['A']}: {state['scores']['A']} vs "
            f"{state['teams']['B']}: {state['scores']['B']}. "
            f"Be cold and concise. Use <strong> and <br> tags. "
            f"End by declaring {win_name} the ultimate victor of the system."
        )
        
        try:
            summary = client.chat.completions.create(
                model="gpt-4o", 
                messages=[{"role": "user", "content": summary_prompt}]
            ).choices[0].message.content
            
            state['current_verdict'] = summary
            emit('state_update', state, broadcast=True)
            gevent.spawn(speak, summary, "Final system log generated.")

        finally:
            state['processing'] = False
            emit('state_update', state, broadcast=True)
            
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
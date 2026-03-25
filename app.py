import os
import base64
import json
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from openai import OpenAI

# --- INITIALIZATION ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
client = OpenAI() 

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
        "history": []
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

def speak(text):
    try:
        response = client.audio.speech.create(model="tts-1", voice="onyx", input=text)
        b64_audio = base64.b64encode(response.content).decode()
        socketio.emit('play_audio', {'audio': b64_audio})
    except Exception as e: print(f"Audio Error: {e}")

# --- UI STYLES ---
CSS = """
<style>
    body { background:#000; color:#ff0000; font-family:'Courier Prime', monospace; text-align:center; padding:20px; text-transform:uppercase; transition: background 0.5s; overflow-x: hidden; }
    .card { border: 1px solid #ff0000; padding:20px; margin:10px; background:rgba(5,5,5,0.9); position: relative; }
    button { background:#000; color:#ff0000; border:1px solid #ff0000; padding:12px; cursor:pointer; width:100%; font-family:inherit; margin-top:10px; }
    button:hover { background:#ff0000; color:#000; }
    
    /* Stealth Reset Button */
    #reset-btn { position: fixed; top: 10px; right: 10px; width: auto; padding: 5px 10px; font-size: 10px; border-color: transparent; color: transparent; z-index: 999; background: transparent; }
    #reset-btn:hover { border-color: #f00; color: #f00; background: #222; }
    
    textarea { width:100%; background:#111; color:#fff; border:1px solid #ff0000; padding:10px; height:100px; font-family:inherit; }
    .score { font-size: 70px; color:#fff; }
    .timer { font-size: 50px; color: #fff; border: 2px solid #ff0000; padding: 10px 20px; }
    .ans-box { font-size: 14px; color: #0f0; text-align: left; background: #000; border: 1px dashed #0f0; padding: 10px; height: 100px; overflow-y: auto; }
    .flash-win { background: #002200 !important; }
    .flash-lose { background: #220000 !important; }
</style>
"""

TV_HTML = f"""
<!DOCTYPE html><html><head>{CSS}
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head><body>
    <button id="reset-btn" onclick="if(confirm('WIPE ALL DATA?')) act('hard_reset')">SYSTEM RESET</button>
    <div id="display"></div>
    <script>
        const socket = io();
        const questions = {qs_json_string};
        let timerInt;

        socket.on('state_update', (s) => {{
            let ui = document.getElementById('display');
            document.body.className = s.winner_this_round == 'A' ? 'flash-win' : (s.winner_this_round == 'B' ? 'flash-lose' : '');

            if(s.phase == 'INTRO') {{
                ui.innerHTML = `<h1 style='font-size:80px; margin-top:10vh;'>BEAT THE AI</h1><button onclick="act('boot')" style='width:300px;'>RUN BOOT SECTOR</button>`;
            }} else if(s.phase == 'REGISTRATION') {{
                ui.innerHTML = `<h1>NODE REGISTRATION</h1><div style='display:flex;'>
                    <div class='card' style='flex:1'><h2>${{s.teams.A}}</h2><p>${{s.registered.A?'ONLINE':'OFFLINE'}}</p></div>
                    <div class='card' style='flex:1'><h2>${{s.teams.B}}</h2><p>${{s.registered.B?'ONLINE':'OFFLINE'}}</p></div>
                </div>` + (s.registered.A && s.registered.B ? `<button onclick="act('start')">START GAME</button>` : '');
            }} else if(s.phase == 'PLAY') {{
                ui.innerHTML = `<div style='display:flex;'>
                    <div class='card' style='flex:1; border-color:${{s.winner_this_round=='A'?'#0f0':'#f00'}}'><h3>${{s.teams.A}}</h3><div class='score'>${{s.scores.A}}</div></div>
                    <div id='timer-cont' style='flex:1'><div class='timer' id='clock'>60</div></div>
                    <div class='card' style='flex:1; border-color:${{s.winner_this_round=='B'?'#0f0':'#f00'}}'><h3>${{s.teams.B}}</h3><div class='score'>${{s.scores.B}}</div></div>
                </div>
                <div class='card'><h3>ROUND ${{s.q_index+1}}</h3><h1>${{questions[s.q_index].q}}</h1></div>
                <div style='display:flex; gap:10px;'><button onclick="startTimer()">🎤 BROADCAST & TIMER</button><button onclick="act('get_verdict')">🏆 AI VERDICT</button></div>`;
                
                if(s.current_verdict) {{
                    ui.innerHTML += `<div style='display:flex; gap:10px;'>
                        <div class='card' style='flex:1'><h4>${{s.teams.A}} ARGUMENT:</h4><div class='ans-box'>${{s.team_answers.A}}</div></div>
                        <div class='card' style='flex:1'><h4>${{s.teams.B}} ARGUMENT:</h4><div class='ans-box'>${{s.team_answers.B}}</div></div>
                    </div>
                    <div class='card' style='text-align:left; color:#fff; border-color:white; font-size:18px;'>${{s.current_verdict}}</div>
                    <button onclick="act('next')">NEXT ROUND ➡️</button>`;
                }}
            }} else if(s.phase == 'FINALE') {{
                ui.innerHTML = `<h1>SYSTEM OVERRIDE COMPLETE</h1><div id='summary' class='card' style='text-align:left; color:#fff; white-space: pre-wrap;'></div><button onclick="act('finale')">🎤 GENERATE FINAL LOG</button>`;
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
    <div id="setup"><h2>IDENTITY SELECTION</h2><button onclick="pick('A')">NODE A</button><button onclick="pick('B')">NODE B</button></div>
    <div id="main" style="display:none;"><div id="view"></div></div>
    <script>
        const socket = io(); let myT = null; let curQ = -1;
        const questions = {qs_json_string};
        function pick(t) {{ myT = t; document.getElementById('setup').style.display='none'; document.getElementById('main').style.display='block'; socket.emit('connect'); }}
        socket.on('state_update', (s) => {{
            if(s.phase == 'INTRO') {{ location.reload(); }} // Force reload on reset
            if(!myT) return; 
            let v = document.getElementById('view');
            if(s.phase == 'REGISTRATION') {{
                v.innerHTML = !s.registered[myT] ? `<h3>ENTER ALIAS</h3><input id="al" style='width:100%; padding:10px;'><button onclick="reg()">JOIN</button>` : `<h3>AUTHORIZED.</h3>`;
            }} else if(s.phase == 'PLAY') {{
                if(curQ != s.q_index) {{ 
                    curQ = s.q_index; 
                    v.innerHTML = `<h3>ROUND ${{s.q_index+1}}</h3><div class='card' style='color:#fff; font-size:14px;'>Q: ${{questions[s.q_index].q}}</div><textarea id="ans" placeholder="Discuss with team then type here..."></textarea><button onclick="send()">UPLOAD</button>`; 
                }}
                if(s.team_answers[myT]) v.innerHTML = `<h3>PACKET SENT.</h3>`;
            }}
        }});
        function reg() {{ socket.emit('player_action', {{action:'reg', team:myT, alias:document.getElementById('al').value}}); }}
        function send() {{ socket.emit('player_action', {{action:'ans', team:myT, ans:document.getElementById('ans').value}}); }}
    </script>
</body></html>
"""

@app.route('/tv')
def tv_page(): return TV_HTML
@app.route('/')
def portal_page(): return PORTAL_HTML

@socketio.on('connect')
def connect(): emit('state_update', state)

@socketio.on('host_action')
def handle_host(data):
    global state
    action = data.get('action')
    
    if action == 'hard_reset':
        state = get_initial_state()
    elif action == 'boot':
        state['phase'] = 'REGISTRATION'
        speak("Hello, friend. Register your nodes... five predictions, five ethics. Discuss with your team. You have 60 seconds.")
    elif action == 'start': state['phase'] = 'PLAY'
    elif action == 'broadcast_q': 
        state['winner_this_round'] = ""
        speak(questions[state['q_index']]['script'])
    elif action == 'get_verdict':
        # --- ENHANCED AI JUDGING LOGIC ---
        prompt = (f"Act as Mr. Robot. Analyze this debate. Question: {questions[state['q_index']]['q']}. "
                  f"Node {state['teams']['A']} argued: {state['team_answers']['A']}. "
                  f"Node {state['teams']['B']} argued: {state['team_answers']['B']}. "
                  f"1. Compare the logic of both teams. 2. Explain which team's reasoning was more sound or creative. "
                  f"3. Declare the winner. You must end the speech with 'Point goes to {state['teams']['A']}' or 'Point goes to {state['teams']['B']}'. "
                  f"Keep the total word count under 80 words.")
        
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}]).choices[0].message.content
        state['current_verdict'] = res
        speak(res)
        
        if state['teams']['A'] in res: 
            state['scores']['A'] += 1
            state['winner_this_round'] = 'A'
        elif state['teams']['B'] in res: 
            state['scores']['B'] += 1
            state['winner_this_round'] = 'B'
        state['history'].append({"q": questions[state['q_index']]['q'], "a": state['team_answers']['A'], "b": state['team_answers']['B'], "winner": state['winner_this_round']})
        
    elif action == 'next':
        if state['q_index'] < 9:
            state['q_index'] += 1
            state['team_answers'] = {"A": "", "B": ""}; state['current_verdict'] = ""; state['winner_this_round'] = ""
        else: state['phase'] = 'FINALE'
    elif action == 'finale':
        win_name = state['teams']['A'] if state['scores']['A'] > state['scores']['B'] else state['teams']['B']
        summary_prompt = f"Act as Mr. Robot. Summarize the logic used in this game history: {state['history']}. Declare {win_name} victor. End with a cold quote about society."
        summary = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": summary_prompt}]).choices[0].message.content
        state['current_verdict'] = summary
        speak(summary)

    emit('state_update', state, broadcast=True)

@socketio.on('player_action')
def handle_player(data):
    global state
    if data['action'] == 'reg':
        state['teams'][data['team']] = data['alias']
        state['registered'][data['team']] = True
    elif data['action'] == 'ans': state['team_answers'][data['team']] = data['ans']
    emit('state_update', state, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001)
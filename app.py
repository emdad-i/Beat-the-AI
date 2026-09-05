# 1. THE MONKEY PATCH (MUST BE FIRST)
from gevent import monkey
monkey.patch_all(socket=False, ssl=False)

# 2. THE SERVER IMPORTS
import base64
import logging
import os
import re
import socket
import time
import traceback

import gevent
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from llm.config import DEFAULT_CHAT_MODEL, DEFAULT_TTS_MODEL, client
from llm.prompts import QUESTIONS, build_get_verdict_prompt, build_summary_prompt

if os.getenv("OPENAI_DEBUG"):
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("openai").setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)

app = Flask(__name__)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="gevent",
    engineio_logger=False,
    always_connect=True,
    transports=["websocket"],
)


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
        "caption": "",
    }


state = get_initial_state()
questions = QUESTIONS
MAX_ANSWER_CHARS = 800


def speak(text, caption=None):
    try:
        if caption:
            state["caption"] = caption
            socketio.emit("state_update", state)

        clean_text = re.sub(r"<[^>]+>", "", text)
        socketio.emit("sync_text", {"text": text})

        max_attempts = 3
        backoff = 1
        for attempt in range(1, max_attempts + 1):
            try:
                with client.audio.speech.with_streaming_response.create(
                    model=DEFAULT_TTS_MODEL,
                    voice="onyx",
                    input=clean_text,
                    response_format="mp3",
                ) as response:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        encoded_chunk = base64.b64encode(chunk).decode()
                        socketio.emit("audio_chunk", {"chunk": encoded_chunk})

                socketio.emit("audio_end")
                break
            except Exception as stream_error:
                trace = traceback.format_exc()
                print(f"Streaming attempt {attempt} failed: {stream_error}\n{trace}")
                socketio.emit(
                    "audio_error",
                    {"error": str(stream_error), "trace": trace, "attempt": attempt},
                )
                if attempt < max_attempts:
                    time.sleep(backoff)
                    backoff *= 2
    except Exception as error:
        trace = traceback.format_exc()
        print(f"Audio Error: {error}\n{trace}")
        socketio.emit("audio_error", {"error": str(error), "trace": trace})
        try:
            fallback_response = client.audio.speech.create(
                model=DEFAULT_TTS_MODEL,
                voice="onyx",
                input=clean_text,
                response_format="mp3",
            )
            for chunk in fallback_response.iter_bytes(chunk_size=65536):
                encoded_chunk = base64.b64encode(chunk).decode()
                socketio.emit("audio_chunk", {"chunk": encoded_chunk})
            socketio.emit("audio_end")
        except Exception as fallback_error:
            fallback_trace = traceback.format_exc()
            print(f"Audio fallback failed: {fallback_error}\n{fallback_trace}")
            socketio.emit(
                "audio_error",
                {"error": str(fallback_error), "trace": fallback_trace, "fallback": True},
            )
            socketio.emit("audio_end")


@app.route("/tv")
def tv_page():
    return render_template("tv.html", questions=questions)


@app.route("/")
def portal_page():
    return render_template("portal.html", questions=questions)


@app.route("/health")
def health():
    return "SYSTEM_ONLINE", 200


@socketio.on("connect")
def connect():
    emit("state_update", state)


@socketio.on("get_current_state")
def handle_get_state():
    emit("state_update", state)


@socketio.on("host_action")
def handle_host(data):
    global state
    action = data.get("action")

    if action == "hard_reset":
        state = get_initial_state()
    elif action == "boot":
        state["phase"] = "REGISTRATION"
        state["caption"] = "Awaiting Node connections..."
    elif action == "start":
        state["phase"] = "PLAY"
        gevent.spawn(
            speak,
            "Hello, friend. We are about to begin. You have 2 and a half minutes to prove your worth.",
            "Hello, friend. We are about to begin...",
        )
    elif action == "broadcast_q":
        state["winner_this_round"] = ""
        gevent.spawn(speak, questions[state["q_index"]]["script"], questions[state["q_index"]]["q"])
    elif action == "get_verdict":
        if state.get("processing"):
            return
        state["processing"] = True
        state["caption"] = "AI is weight-testing logic packets..."
        emit("state_update", state, broadcast=True)
        prompt = build_get_verdict_prompt(state, questions[state["q_index"]])
        try:
            result = client.chat.completions.create(
                model=DEFAULT_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a cyber-security judge. You compare two arguments and pick a winner based on logic and conviction."},
                    {"role": "user", "content": prompt},
                ],
            ).choices[0].message.content
            state["current_verdict"] = result
            result_marker = result.upper().split("RESULT:")[-1]
            if f"RESULT: [{state['teams']['A']}]" in result:
                state["scores"]["A"] += 1
                state["winner_this_round"] = "A"
            elif f"RESULT: [{state['teams']['B']}]" in result:
                state["scores"]["B"] += 1
                state["winner_this_round"] = "B"
            elif state["teams"]["A"].upper() in result_marker:
                state["scores"]["A"] += 1
                state["winner_this_round"] = "A"
            elif state["teams"]["B"].upper() in result_marker:
                state["scores"]["B"] += 1
                state["winner_this_round"] = "B"
            state["history"].append({
                "q": questions[state["q_index"]]["q"],
                "winner": state["teams"]["A"] if state["winner_this_round"] == "A" else state["teams"]["B"],
            })
            emit("state_update", state, broadcast=True)
            gevent.spawn(speak, result, "Comparison complete. Winner identified.")
        finally:
            state["processing"] = False
    elif action == "intro_sequence":
        gevent.spawn(
            speak,
            "Welcome to the system. Nodes initialized. Prepare for data extraction. Let the games begin.",
            "INITIALIZING FSOCIETY PROTOCOL...",
        )
    elif action == "next":
        if state["q_index"] >= len(questions) - 1:
            state["phase"] = "FINALE"
            state["current_verdict"] = ""
            state["winner_this_round"] = ""
            state["caption"] = "SYSTEM OVERRIDE COMPLETE. FINALIZING LOGS..."
        else:
            state["q_index"] += 1
            state["team_answers"] = {"A": "", "B": ""}
            state["current_verdict"] = ""
            state["winner_this_round"] = ""
            state["caption"] = f"Awaiting data for Round {state['q_index'] + 1}..."
        emit("state_update", state, broadcast=True)
    elif action == "finale":
        if state.get("processing"):
            return
        state["processing"] = True
        emit("state_update", state, broadcast=True)
        summary_prompt = build_summary_prompt(state)
        try:
            summary = client.chat.completions.create(
                model=DEFAULT_CHAT_MODEL,
                messages=[{"role": "user", "content": summary_prompt}],
            ).choices[0].message.content
            state["current_verdict"] = summary
            emit("state_update", state, broadcast=True)
            gevent.spawn(speak, summary, "Final system log generated.")
        finally:
            state["processing"] = False
            emit("state_update", state, broadcast=True)

    emit("state_update", state, broadcast=True)


@socketio.on("player_action")
def handle_player(data):
    global state
    if data["action"] == "reg":
        state["teams"][data["team"]] = data["alias"]
        state["registered"][data["team"]] = True
    elif data["action"] == "ans":
        state["team_answers"][data["team"]] = data["ans"][:MAX_ANSWER_CHARS]
    emit("state_update", state, broadcast=True)


def get_local_ip():
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        connection.connect(("10.255.255.255", 1))
        local_ip = connection.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        connection.close()
    return local_ip


if __name__ == "__main__":
    port = 5001
    local_ip = get_local_ip()
    print("\n" + "=" * 50)
    print("FSOCIETY OVERRIDE: SYSTEM ONLINE")
    print(f"LOCAL NETWORK IP: {local_ip}")
    print(f"TV SCREEN:    http://{local_ip}:{port}/tv")
    print(f"PLAYER PORTAL: http://{local_ip}:{port}/")
    print("=" * 50 + "\n")
    http_server = WSGIServer(("0.0.0.0", port), app, handler_class=WebSocketHandler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping System...")
const socket = io({ transports: ['websocket'], upgrade: false });
const questions = window.QUESTIONS;
let timerInt;

const mediaSource = new MediaSource();
let sourceBuffer = null;
const audioQueue = [];
let isAppending = false;
const audioPlayer = new Audio();
audioPlayer.src = URL.createObjectURL(mediaSource);
audioPlayer.playbackRate = 1.15;

mediaSource.addEventListener('sourceopen', () => {
    sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
    sourceBuffer.addEventListener('updateend', () => {
        isAppending = false;
        processQueue();
    });
});

socket.on('audio_chunk', (data) => {
    const binary = atob(data.chunk);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
    }
    audioQueue.push(bytes);
    processQueue();
});

function processQueue() {
    if (!sourceBuffer || isAppending || audioQueue.length === 0 || sourceBuffer.updating) {
        return;
    }

    isAppending = true;
    try {
        sourceBuffer.appendBuffer(audioQueue.shift());
    } catch (error) {
        isAppending = false;
    }

    if (audioPlayer.paused) {
        audioPlayer.play().catch(() => {});
    }
}

socket.on('sync_text', (data) => {
    const container = document.querySelector('.verdict-text');
    if (container) {
        container.innerHTML = formatVerdict(data.text);
        container.style.opacity = 1;
    }
});

function formatVerdict(text) {
    const decoder = document.createElement('textarea');
    decoder.innerHTML = text;
    let formatted = decoder.value.trim();

    formatted = formatted
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/<br\s*\/?\s*>/gi, '<br>');

    if (!/<\/?(strong|br)\b/i.test(formatted)) {
        formatted = formatted.replace(/\r?\n/g, '<br>');
    }

    return formatted;
}

socket.on('state_update', (state) => {
    const display = document.getElementById('display');
    document.body.className = state.winner_this_round === 'A'
        ? 'flash-win'
        : (state.winner_this_round === 'B' ? 'flash-lose' : '');

    if (state.phase === 'INTRO') {
        display.innerHTML = `
            <h1 style="font-size:80px; margin-top:10vh;">BEAT THE AI</h1>
            <div style="display:flex; gap:10px; justify-content:center;">
                <button onclick="act('intro_sequence')" style="width:200px; border-color:#0f0; color:#0f0;">INITIATE INTRO</button>
                <button onclick="act('boot')" style="width:200px;">RUN BOOT SECTOR</button>
            </div>
            <div class="caption-box">${state.caption}</div>`;
    } else if (state.phase === 'REGISTRATION') {
        display.innerHTML = `<h1>NODE REGISTRATION</h1><div style="display:flex;">
            <div class="card" style="flex:1"><h2>${state.teams.A}</h2><p class="${state.registered.A ? 'online' : 'offline'}">${state.registered.A ? 'ONLINE' : 'OFFLINE'}</p></div>
            <div class="card" style="flex:1"><h2>${state.teams.B}</h2><p class="${state.registered.B ? 'online' : 'offline'}">${state.registered.B ? 'ONLINE' : 'OFFLINE'}</p></div>
        </div>${state.registered.A && state.registered.B ? '<button onclick="act(\'start\')">START GAME</button>' : ''}<div class="caption-box">${state.caption}</div>`;
    } else if (state.phase === 'PLAY') {
        const aSubmitted = state.team_answers.A !== '';
        const bSubmitted = state.team_answers.B !== '';
        const bothSubmitted = aSubmitted && bSubmitted;

        display.innerHTML = `<div style="display:flex;">
            <div class="card ${aSubmitted ? 'submitted' : 'waiting'}" style="flex:1;"><h3>${state.teams.A}</h3><div class="score">${state.scores.A}</div></div>
            <div id="timer-cont" style="flex:1"><div class="timer" id="clock">02:30</div></div>
            <div class="card ${bSubmitted ? 'submitted' : 'waiting'}" style="flex:1;"><h3>${state.teams.B}</h3><div class="score">${state.scores.B}</div></div>
        </div>
        <div class="card"><h3>ROUND ${state.q_index + 1}</h3><h1>${questions[state.q_index].q}</h1></div>
        <button onclick="startTimer()">🎤 BROADCAST & TIMER</button>
        <button onclick="act('get_verdict')" ${(!bothSubmitted || state.processing) ? 'disabled' : ''}>
            ${state.processing ? 'ANALYZING...' : '🏆 AI VERDICT'}
        </button>`;

        if (state.current_verdict) {
            display.innerHTML += `
                <div class="card verdict-text" style="color:#fff; opacity:0;">${formatVerdict(state.current_verdict)}</div>
                <button onclick="act('next')">NEXT</button>`;
        }
    } else if (state.phase === 'FINALE') {
        display.innerHTML = `
            <h1 style="font-size:60px; color:#0f0;">SYSTEM OVERRIDE COMPLETE</h1>
            <div class="card">
                <div id="summary" class="verdict-text" style="color:#fff; font-size:1.2rem;">
                    ${state.current_verdict ? formatVerdict(state.current_verdict) : 'PREPARING FINAL LOG... Wait for it.'}
                </div>
            </div>
            ${!state.current_verdict
                ? '<button onclick="act(\'finale\')" style="border-color:#0f0; color:#0f0;">GENERATE FINAL LOG</button>'
                : '<button onclick="act(\'hard_reset\')">REBOOT SYSTEM</button>'}`;
    }
});

function act(action, team = null) {
    socket.emit('host_action', { action, team });
}

function startTimer() {
    act('broadcast_q');
    let remaining = 150;
    clearInterval(timerInt);
    timerInt = setInterval(() => {
        remaining -= 1;
        const minutes = Math.floor(remaining / 60).toString().padStart(2, '0');
        const seconds = (remaining % 60).toString().padStart(2, '0');
        const clock = document.getElementById('clock');
        if (clock) {
            clock.innerText = `${minutes}:${seconds}`;
        }
        if (remaining <= 0) {
            clearInterval(timerInt);
        }
    }, 1000);
}

const socket = io({ transports: ['websocket'], upgrade: false });
let myTeam = null;
let currentQuestion = -1;
const questions = window.QUESTIONS;

socket.on('disconnect', () => {
    console.log('Lost connection to fsociety server...');
    setTimeout(() => {
        location.reload();
    }, 3000);
});

function pick(team) {
    myTeam = team;
    document.getElementById('setup').style.display = 'none';
    document.getElementById('main').style.display = 'block';
    socket.emit('get_current_state');
}

socket.on('state_update', (state) => {
    if (!myTeam) {
        return;
    }

    const view = document.getElementById('view');

    if (state.phase === 'INTRO') {
        view.innerHTML = '<h3>WAITING FOR HOST TO BOOT SYSTEM...</h3>';
    } else if (state.phase === 'REGISTRATION') {
        if (!state.registered[myTeam]) {
            view.innerHTML = `
                <h3>NODE ${myTeam} ACCESS</h3>
                <p>ENTER ALIAS TO INITIALIZE</p>
                <input id="al" style="width:100%; padding:10px; background:#111; color:#0f0; border:1px solid #0f0;">
                <button onclick="reg()">JOIN NETWORK</button>`;
        } else {
            view.innerHTML = '<h3 style="color:#0f0;">UNLOCKED.</h3><p>WAITING FOR TARGET DATA...</p>';
        }
    } else if (state.phase === 'PLAY') {
        if (currentQuestion !== state.q_index) {
            currentQuestion = state.q_index;
            view.innerHTML = `
                <h3>ROUND ${state.q_index + 1}</h3>
                <div class="card" style="color:#fff; font-size:14px;">Q: ${questions[state.q_index].q}</div>
                <textarea id="ans" placeholder="Type your argument here..."></textarea>
                <button onclick="send()">UPLOAD DATA</button>`;
        }
        if (state.team_answers[myTeam]) {
            view.innerHTML = '<h3 style="color:#0f0;">PACKET SENT.</h3><p>AWAITING AI VERDICT...</p>';
        }
    }
});

function reg() {
    const alias = document.getElementById('al').value;
    if (alias) {
        socket.emit('player_action', { action: 'reg', team: myTeam, alias });
    }
}

function send() {
    const answer = document.getElementById('ans').value;
    if (answer) {
        socket.emit('player_action', { action: 'ans', team: myTeam, ans: answer });
    }
}

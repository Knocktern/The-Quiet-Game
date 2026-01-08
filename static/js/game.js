/**
 * Sign Language Guessing Game - Client Side Logic
 * 
 * Handles game state, WebRTC video, and real-time communication
 */

// =============================================================================
// Game State
// =============================================================================

const gameState = {
    socket: null,
    roomCode: null,
    userId: null,
    username: null,
    isActor: false,
    currentWord: null,
    gameStarted: false,
    localStream: null,
    peerConnections: {},
    remoteStreams: {},
    players: {},
    timerInterval: null,
    timeRemaining: 60
};

// WebRTC Configuration
const rtcConfig = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeSocket();
    initializeUIHandlers();
    generateUserId();
});

function generateUserId() {
    gameState.userId = 'user_' + Math.random().toString(36).substr(2, 9);
}

function generateRoomCode() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let code = '';
    for (let i = 0; i < 4; i++) code += chars.charAt(Math.floor(Math.random() * chars.length));
    code += '-';
    for (let i = 0; i < 4; i++) code += chars.charAt(Math.floor(Math.random() * chars.length));
    return code;
}

// =============================================================================
// Socket.IO Connection
// =============================================================================

function initializeSocket() {
    gameState.socket = io();

    // Connection events
    gameState.socket.on('connect', () => {
        console.log('Connected to server');
    });

    gameState.socket.on('error', (data) => {
        showNotification(data.message, 'error');
    });

    // Game events
    gameState.socket.on('game-state', handleGameState);
    gameState.socket.on('player-joined', handlePlayerJoined);
    gameState.socket.on('player-left', handlePlayerLeft);
    gameState.socket.on('player-ready-update', handleReadyUpdate);
    gameState.socket.on('game-started', handleGameStarted);
    gameState.socket.on('word-choices', handleWordChoices);
    gameState.socket.on('your-word', handleYourWord);
    gameState.socket.on('round-started', handleRoundStarted);
    gameState.socket.on('guess-made', handleGuessMade);
    gameState.socket.on('correct-guess', handleCorrectGuess);
    gameState.socket.on('hint', handleHint);
    gameState.socket.on('round-ended', handleRoundEnded);
    gameState.socket.on('next-round', handleNextRound);
    gameState.socket.on('game-over', handleGameOver);
    gameState.socket.on('chat-message', handleChatMessage);

    // WebRTC events
    gameState.socket.on('offer', handleOffer);
    gameState.socket.on('answer', handleAnswer);
    gameState.socket.on('ice-candidate', handleIceCandidate);
}

// =============================================================================
// UI Handlers
// =============================================================================

function initializeUIHandlers() {
    // Lobby
    document.getElementById('createRoomBtn').addEventListener('click', createRoom);
    document.getElementById('joinRoomBtn').addEventListener('click', joinRoom);
    
    // Waiting Room
    document.getElementById('copyCodeBtn').addEventListener('click', copyRoomCode);
    document.getElementById('readyBtn').addEventListener('click', toggleReady);
    document.getElementById('startGameBtn').addEventListener('click', startGame);
    document.getElementById('leaveLobbyBtn').addEventListener('click', leaveLobby);
    
    // Game
    document.getElementById('sendGuessBtn').addEventListener('click', sendGuess);
    document.getElementById('guessInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendGuess();
    });
    document.getElementById('toggleVideoBtn').addEventListener('click', toggleVideo);
    document.getElementById('toggleAudioBtn').addEventListener('click', toggleAudio);
    document.getElementById('hintBtn').addEventListener('click', requestHint);
    
    // Game Over
    document.getElementById('playAgainBtn').addEventListener('click', playAgain);
    document.getElementById('exitGameBtn').addEventListener('click', exitGame);
    
    // Room code formatting
    document.getElementById('roomCodeInput').addEventListener('input', formatRoomCodeInput);
}

function formatRoomCodeInput(e) {
    let value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (value.length > 4) {
        value = value.slice(0, 4) + '-' + value.slice(4, 8);
    }
    e.target.value = value;
}

// =============================================================================
// Room Management
// =============================================================================

async function createRoom() {
    const username = document.getElementById('usernameCreate').value.trim();
    if (!username) {
        showNotification('Please enter your name', 'error');
        return;
    }

    gameState.username = username;
    gameState.roomCode = generateRoomCode();

    await initializeMedia();
    joinGameRoom();
}

async function joinRoom() {
    const username = document.getElementById('usernameJoin').value.trim();
    const roomCode = document.getElementById('roomCodeInput').value.trim().toUpperCase();

    if (!username) {
        showNotification('Please enter your name', 'error');
        return;
    }
    if (!roomCode || roomCode.length < 9) {
        showNotification('Please enter a valid room code', 'error');
        return;
    }

    gameState.username = username;
    gameState.roomCode = roomCode;

    await initializeMedia();
    joinGameRoom();
}

function joinGameRoom() {
    gameState.socket.emit('join-game', {
        roomCode: gameState.roomCode,
        userId: gameState.userId,
        username: gameState.username
    });

    showSection('waitingRoom');
    document.getElementById('displayRoomCode').textContent = gameState.roomCode;
    
    // Start connection health check
    startConnectionHealthCheck();
}

function copyRoomCode() {
    navigator.clipboard.writeText(gameState.roomCode);
    showNotification('Room code copied!', 'success');
}

function copyGameRoomCode() {
    const roomCode = document.getElementById('gameRoomCode').textContent;
    navigator.clipboard.writeText(roomCode);
    showNotification('Room code copied! Share it with friends to join mid-game!', 'success');
}

function toggleReady() {
    const btn = document.getElementById('readyBtn');
    const isReady = btn.classList.toggle('ready');
    btn.textContent = isReady ? 'Not Ready' : 'Ready!';
    
    gameState.socket.emit('player-ready', {
        roomCode: gameState.roomCode,
        userId: gameState.userId,
        isReady: isReady
    });
}

function startGame() {
    const difficulty = document.getElementById('difficultySelect').value;
    gameState.socket.emit('start-game', {
        roomCode: gameState.roomCode,
        difficulty: difficulty
    });
}

function leaveLobby() {
    gameState.socket.emit('leave-game', {
        roomCode: gameState.roomCode,
        userId: gameState.userId
    });
    
    cleanup();
    showSection('lobby');
}

// =============================================================================
// Media Handling
// =============================================================================

async function initializeMedia() {
    try {
        gameState.localStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: true
        });
        
        document.getElementById('localVideo').srcObject = gameState.localStream;
        return true;
    } catch (error) {
        console.error('Error accessing media devices:', error);
        showNotification('Could not access camera/microphone', 'error');
        return false;
    }
}

function toggleVideo() {
    if (gameState.localStream) {
        const videoTrack = gameState.localStream.getVideoTracks()[0];
        if (videoTrack) {
            videoTrack.enabled = !videoTrack.enabled;
            document.getElementById('toggleVideoBtn').textContent = videoTrack.enabled ? '📹' : '📷';
        }
    }
}

function toggleAudio() {
    if (gameState.localStream) {
        const audioTrack = gameState.localStream.getAudioTracks()[0];
        if (audioTrack) {
            audioTrack.enabled = !audioTrack.enabled;
            document.getElementById('toggleAudioBtn').textContent = audioTrack.enabled ? '🔇' : '🔊';
        }
    }
}

// =============================================================================
// WebRTC Peer Connections
// =============================================================================

async function createPeerConnection(peerId) {
    // Close existing connection if any
    if (gameState.peerConnections[peerId]) {
        try {
            gameState.peerConnections[peerId].close();
        } catch (e) {
            console.log('Error closing existing connection:', e);
        }
        delete gameState.peerConnections[peerId];
    }

    const pc = new RTCPeerConnection(rtcConfig);
    gameState.peerConnections[peerId] = pc;

    // Add local stream tracks
    if (gameState.localStream) {
        gameState.localStream.getTracks().forEach(track => {
            pc.addTrack(track, gameState.localStream);
        });
    }

    // Handle incoming tracks
    pc.ontrack = (event) => {
        console.log('Received track from', peerId, event.streams);
        
        // Store the remote stream for this peer
        if (!gameState.remoteStreams) {
            gameState.remoteStreams = {};
        }
        gameState.remoteStreams[peerId] = event.streams[0];
        
        // Update actor video if this peer is the actor
        if (gameState.players[peerId] && gameState.players[peerId].isActor) {
            const actorVideo = document.getElementById('actorVideo');
            actorVideo.srcObject = event.streams[0];
        }
        
        // If we're the actor, show our own video
        if (gameState.isActor) {
            const actorVideo = document.getElementById('actorVideo');
            actorVideo.srcObject = gameState.localStream;
        }
        
        // Update participants grid with the new stream
        if (gameState.gameStarted) {
            updateParticipantsGrid();
        }
    };

    // Handle ICE candidates - send to specific peer
    pc.onicecandidate = (event) => {
        if (event.candidate && gameState.roomCode) {
            gameState.socket.emit('ice-candidate', {
                roomCode: gameState.roomCode,
                userId: gameState.userId,
                targetId: peerId,
                candidate: event.candidate
            });
        }
    };

    // Handle connection state changes
    pc.onconnectionstatechange = () => {
        console.log(`Connection state with ${peerId}: ${pc.connectionState}`);
        if (pc.connectionState === 'failed') {
            console.log('Connection failed, attempting reconnect...');
            // Retry connection after a delay
            setTimeout(() => {
                if (gameState.players[peerId]) {
                    initiateConnection(peerId);
                }
            }, 2000);
        }
    };

    pc.oniceconnectionstatechange = () => {
        console.log(`ICE connection state with ${peerId}: ${pc.iceConnectionState}`);
    };

    return pc;
}

async function handleOffer(data) {
    if (!data) return;
    
    const { offer, userId: peerId, targetId } = data;
    
    // Only process offers meant for us
    if (targetId && targetId !== gameState.userId) return;
    
    // Don't process our own offers
    if (!peerId || peerId === gameState.userId) return;
    
    console.log('Received offer from', peerId, 'for', targetId);
    
    try {
        const pc = await createPeerConnection(peerId);
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        
        gameState.socket.emit('answer', {
            roomCode: gameState.roomCode,
            userId: gameState.userId,
            targetId: peerId,
            answer: answer
        });
        
        console.log('Sent answer to', peerId);
    } catch (e) {
        console.error('Error handling offer:', e);
    }
}

async function handleAnswer(data) {
    if (!data) return;
    
    const { answer, userId: peerId, targetId } = data;
    
    // Only process answers meant for us
    if (targetId && targetId !== gameState.userId) return;
    if (!peerId || peerId === gameState.userId) return;
    
    const pc = gameState.peerConnections[peerId];
    
    if (pc && pc.signalingState === 'have-local-offer') {
        try {
            console.log('Received answer from', peerId);
            await pc.setRemoteDescription(new RTCSessionDescription(answer));
        } catch (e) {
            console.error('Error handling answer:', e);
        }
    }
}

async function handleIceCandidate(data) {
    if (!data) return;
    
    const { candidate, userId: peerId, targetId } = data;
    
    // Only process ICE candidates meant for us
    if (targetId && targetId !== gameState.userId) return;
    if (!peerId || peerId === gameState.userId) return;
    
    const pc = gameState.peerConnections[peerId];
    
    if (pc && candidate) {
        try {
            await pc.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (e) {
            console.error('Error adding ICE candidate:', e);
        }
    }
}

async function initiateConnection(peerId) {
    if (!peerId || peerId === gameState.userId) return;
    
    // Skip if already have an active connection
    const existingPc = gameState.peerConnections[peerId];
    if (existingPc && (existingPc.connectionState === 'connected' || existingPc.connectionState === 'connecting')) {
        console.log('Already connected/connecting to', peerId);
        return;
    }
    
    // Use a consistent rule: lower ID initiates the connection
    // This prevents both sides from sending offers simultaneously
    if (gameState.userId > peerId) {
        console.log('Waiting for offer from', peerId, '(they have lower ID)');
        return; // Let the other peer initiate
    }
    
    console.log('Initiating connection to', peerId);
    
    try {
        const pc = await createPeerConnection(peerId);
        
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        
        gameState.socket.emit('offer', {
            roomCode: gameState.roomCode,
            userId: gameState.userId,
            targetId: peerId,  // Specify the target peer
            offer: offer
        });
        
        console.log('Sent offer to', peerId);
    } catch (e) {
        console.error('Error initiating connection:', e);
        // Retry after delay
        setTimeout(() => {
            if (gameState.players[peerId]) {
                delete gameState.peerConnections[peerId];
                initiateConnection(peerId);
            }
        }, 3000);
    }
}

// =============================================================================
// Game Event Handlers
// =============================================================================

function handleGameState(data) {
    gameState.players = {};
    
    for (const [id, player] of Object.entries(data.players)) {
        gameState.players[id] = {
            username: player.username,
            score: player.score,
            isReady: player.is_ready,
            isActor: data.current_actor === id
        };
    }
    
    updatePlayersList();
    updateLeaderboard(data.leaderboard);
    
    // Check if this is a mid-game join
    if (data.is_mid_game_join && data.game_started && !data.game_ended) {
        console.log('Mid-game join detected, entering active game...');
        gameState.gameStarted = true;
        
        // Show game area instead of waiting room
        showSection('gameArea');
        document.getElementById('gameRoomCode').textContent = gameState.roomCode;
        document.getElementById('maxRounds').textContent = data.max_rounds;
        document.getElementById('currentRound').textContent = data.current_round || 1;
        
        // Set up actor UI
        if (data.current_actor) {
            gameState.isActor = data.current_actor === gameState.userId;
            updateActorUI(data.current_actor);
        }
        
        // Set up round info if available
        if (data.round_info) {
            const guessInput = document.getElementById('guessInput');
            const guessBtn = document.getElementById('sendGuessBtn');
            
            if (gameState.isActor) {
                guessInput.disabled = true;
                guessInput.placeholder = "You're acting this round!";
                guessBtn.disabled = true;
            } else {
                guessInput.disabled = false;
                guessInput.placeholder = `Guess the ${data.round_info.category} (${data.round_info.word_length} letters)`;
                guessBtn.disabled = false;
            }
            
            // Start timer with remaining time
            if (data.round_info.time_remaining > 0) {
                startTimer(data.round_info.time_remaining);
            }
        }
        
        addChatMessage('system', 'You joined the game in progress!');
    }
    
    // Initiate connections with ALL other players
    // Each player will initiate connections to players with higher IDs
    setTimeout(() => {
        Object.keys(data.players).forEach(playerId => {
            if (playerId !== gameState.userId) {
                initiateConnection(playerId);
            }
        });
    }, 500);
}

function handlePlayerJoined(data) {
    gameState.players[data.userId] = {
        username: data.username,
        score: 0,
        isReady: false,
        isActor: false
    };
    
    updatePlayersList();
    
    // Different message for mid-game join
    if (data.isMidGameJoin) {
        addChatMessage('system', `${data.username} joined the game in progress!`);
    } else {
        addChatMessage('system', `${data.username} joined the game`);
    }
    
    // Update participants grid if game is in progress
    if (gameState.gameStarted) {
        updateParticipantsGrid();
    }
    
    // Initiate connection with new player after a short delay
    // The new player has a higher chance of having a "newer" ID, so we should try to connect
    setTimeout(() => {
        initiateConnection(data.userId);
    }, 800);
}

function handlePlayerLeft(data) {
    const player = gameState.players[data.userId];
    if (player) {
        addChatMessage('system', `${player.username} left the game`);
        delete gameState.players[data.userId];
    }
    
    if (gameState.peerConnections[data.userId]) {
        try {
            gameState.peerConnections[data.userId].close();
        } catch (e) {
            console.log('Error closing connection:', e);
        }
        delete gameState.peerConnections[data.userId];
    }
    
    if (gameState.remoteStreams && gameState.remoteStreams[data.userId]) {
        delete gameState.remoteStreams[data.userId];
    }
    
    updatePlayersList();
    
    // Update participants grid if game is in progress
    if (gameState.gameStarted) {
        updateParticipantsGrid();
    }
    
    if (data.gameState && data.gameState.leaderboard) {
        updateLeaderboard(data.gameState.leaderboard);
    }
}

function handleReadyUpdate(data) {
    if (gameState.players[data.userId]) {
        gameState.players[data.userId].isReady = data.isReady;
    }
    
    updatePlayersList();
    
    // Show/hide start button for room creator
    const startBtn = document.getElementById('startGameBtn');
    if (data.allReady && Object.keys(gameState.players).length >= 2) {
        startBtn.classList.remove('hidden');
        startBtn.disabled = false;
    }
}

function handleGameStarted(data) {
    gameState.gameStarted = true;
    showSection('gameArea');
    
    document.getElementById('gameRoomCode').textContent = gameState.roomCode;
    document.getElementById('maxRounds').textContent = data.gameState.max_rounds;
    
    updateLeaderboard(data.gameState.leaderboard);
    
    // Check if we're the actor
    gameState.isActor = data.actorId === gameState.userId;
    updateActorUI(data.actorId);
}

function handleWordChoices(data) {
    if (!gameState.isActor) return;
    
    const container = document.getElementById('wordChoices');
    container.innerHTML = '';
    
    data.words.forEach(word => {
        const btn = document.createElement('button');
        btn.className = 'word-choice-btn';
        btn.innerHTML = `
            <span class="word">${word.word}</span>
            <span class="category">${word.category}</span>
        `;
        btn.addEventListener('click', () => selectWord(word));
        container.appendChild(btn);
    });
    
    document.getElementById('wordSelection').classList.remove('hidden');
}

function selectWord(word) {
    gameState.socket.emit('select-word', {
        roomCode: gameState.roomCode,
        userId: gameState.userId,
        word: word
    });
    
    document.getElementById('wordSelection').classList.add('hidden');
}

function handleYourWord(data) {
    if (!gameState.isActor) return;
    
    gameState.currentWord = data.word;
    document.getElementById('wordCategory').textContent = data.category;
    document.getElementById('wordToAct').textContent = data.word.toUpperCase();
    document.getElementById('wordDisplay').classList.remove('hidden');
}

function handleRoundStarted(data) {
    document.getElementById('currentRound').textContent = data.roundNumber;
    
    // Update actor display
    gameState.isActor = data.actorId === gameState.userId;
    updateActorUI(data.actorId);
    
    // Start timer
    startTimer(60);
    
    // Disable/enable guess input based on role
    const guessInput = document.getElementById('guessInput');
    const guessBtn = document.getElementById('sendGuessBtn');
    
    if (gameState.isActor) {
        guessInput.disabled = true;
        guessInput.placeholder = "You're acting this round!";
        guessBtn.disabled = true;
    } else {
        guessInput.disabled = false;
        guessInput.placeholder = `Guess the ${data.category} (${data.wordLength} letters)`;
        guessBtn.disabled = false;
    }
    
    addChatMessage('system', `Round ${data.roundNumber} started! Category: ${data.category}`);
}

function handleGuessMade(data) {
    addChatMessage(data.username, data.guess, false);
}

function handleCorrectGuess(data) {
    addChatMessage('correct', `🎉 ${data.username} guessed correctly! +${data.points} points`);
    updateLeaderboard(data.leaderboard);
}

function handleHint(data) {
    addChatMessage('hint', `💡 Hint: ${data.hint}`);
}

function handleRoundEnded(data) {
    stopTimer();
    
    // Show word reveal overlay
    document.getElementById('revealedWord').textContent = data.word.toUpperCase();
    
    const stats = document.getElementById('roundStats');
    const correctCount = data.summary.correct_guessers ? data.summary.correct_guessers.length : 0;
    stats.textContent = `${correctCount} player(s) guessed correctly`;
    
    if (data.gameEnded) {
        document.getElementById('nextRoundInfo').textContent = 'Game Over!';
    } else {
        document.getElementById('nextRoundInfo').textContent = 'Next round starting in 5 seconds...';
    }
    
    document.getElementById('wordRevealOverlay').classList.remove('hidden');
    document.getElementById('wordDisplay').classList.add('hidden');
    
    // Hide overlay after delay
    setTimeout(() => {
        document.getElementById('wordRevealOverlay').classList.add('hidden');
    }, 5000);
    
    updateLeaderboard(data.gameState.leaderboard);
}

function handleNextRound(data) {
    gameState.isActor = data.actorId === gameState.userId;
    updateActorUI(data.actorId);
    
    if (gameState.isActor) {
        handleWordChoices(data);
    }
}

function handleGameOver(data) {
    document.getElementById('wordRevealOverlay').classList.add('hidden');
    
    const winner = data.results.winner;
    const announcement = document.getElementById('winnerAnnouncement');
    announcement.innerHTML = `
        <div class="winner-trophy">🏆</div>
        <div class="winner-name">${winner ? winner.username : 'No winner'}</div>
        <div class="winner-score">${winner ? winner.score + ' points' : ''}</div>
    `;
    
    const leaderboard = document.getElementById('finalLeaderboard');
    leaderboard.innerHTML = data.results.leaderboard.map((p, i) => `
        <div class="final-rank ${i === 0 ? 'first' : ''}">
            <span class="rank">#${p.rank}</span>
            <span class="name">${p.username}</span>
            <span class="score">${p.score}</span>
        </div>
    `).join('');
    
    document.getElementById('gameOverOverlay').classList.remove('hidden');
}

function handleChatMessage(data) {
    addChatMessage(data.username, data.message);
}

// =============================================================================
// Game Actions
// =============================================================================

function sendGuess() {
    const input = document.getElementById('guessInput');
    const guess = input.value.trim();
    
    if (!guess || gameState.isActor) return;
    
    gameState.socket.emit('submit-guess', {
        roomCode: gameState.roomCode,
        userId: gameState.userId,
        guess: guess
    });
    
    input.value = '';
}

function requestHint() {
    if (gameState.isActor) return;
    
    gameState.socket.emit('request-hint', {
        roomCode: gameState.roomCode
    });
}

function playAgain() {
    document.getElementById('gameOverOverlay').classList.add('hidden');
    gameState.gameStarted = false;
    showSection('waitingRoom');
}

function exitGame() {
    gameState.socket.emit('leave-game', {
        roomCode: gameState.roomCode,
        userId: gameState.userId
    });
    
    cleanup();
    showSection('lobby');
}

// =============================================================================
// UI Updates
// =============================================================================

function showSection(sectionId) {
    document.querySelectorAll('.game-section').forEach(section => {
        section.classList.add('hidden');
    });
    document.getElementById(sectionId).classList.remove('hidden');
}

function updatePlayersList() {
    const list = document.getElementById('playersList');
    list.innerHTML = '';
    
    Object.entries(gameState.players).forEach(([id, player]) => {
        const li = document.createElement('li');
        li.className = player.isReady ? 'ready' : '';
        li.innerHTML = `
            <span class="player-name">${player.username}</span>
            <span class="player-status">${player.isReady ? '✅' : '⏳'}</span>
            ${id === gameState.userId ? '<span class="you-badge">(You)</span>' : ''}
        `;
        list.appendChild(li);
    });
    
    document.getElementById('playerCount').textContent = Object.keys(gameState.players).length;
}

function updateLeaderboard(leaderboard) {
    const list = document.getElementById('leaderboard');
    list.innerHTML = '';
    
    leaderboard.forEach((player, i) => {
        const li = document.createElement('li');
        li.className = player.user_id === gameState.userId ? 'you' : '';
        li.innerHTML = `
            <span class="rank">${i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '#' + (i + 1)}</span>
            <span class="name">${player.username}</span>
            <span class="score">${player.score}</span>
        `;
        list.appendChild(li);
    });
}

function updateParticipantsGrid() {
    const grid = document.getElementById('participantsGrid');
    if (!grid) return;
    
    // Get existing participant IDs in the grid
    const existingIds = new Set();
    grid.querySelectorAll('.participant-video-wrapper').forEach(wrapper => {
        const id = wrapper.id.replace('participant-', '');
        existingIds.add(id);
    });
    
    // Get current player IDs
    const currentPlayerIds = new Set(Object.keys(gameState.players));
    
    // Remove participants who left
    existingIds.forEach(id => {
        if (!currentPlayerIds.has(id)) {
            const wrapper = document.getElementById(`participant-${id}`);
            if (wrapper) wrapper.remove();
        }
    });
    
    // Add or update all participants
    Object.entries(gameState.players).forEach(([id, player]) => {
        let wrapper = document.getElementById(`participant-${id}`);
        let video;
        
        if (!wrapper) {
            // Create new wrapper
            wrapper = document.createElement('div');
            wrapper.className = 'participant-video-wrapper';
            wrapper.id = `participant-${id}`;
            
            video = document.createElement('video');
            video.autoplay = true;
            video.playsinline = true;
            video.muted = id === gameState.userId;
            
            const label = document.createElement('div');
            label.className = 'participant-label' + (id === gameState.userId ? ' you' : '');
            label.textContent = player.username + (id === gameState.userId ? ' (You)' : '');
            
            wrapper.appendChild(video);
            wrapper.appendChild(label);
            grid.appendChild(wrapper);
        } else {
            video = wrapper.querySelector('video');
        }
        
        // Update actor highlight
        if (player.isActor) {
            wrapper.classList.add('is-actor');
        } else {
            wrapper.classList.remove('is-actor');
        }
        
        // Set video source if not already set or if different
        const expectedStream = id === gameState.userId 
            ? gameState.localStream 
            : (gameState.remoteStreams && gameState.remoteStreams[id]);
        
        if (video && expectedStream && video.srcObject !== expectedStream) {
            video.srcObject = expectedStream;
            video.play().catch(e => console.log('Video play error:', e));
        }
    });
}

function updateActorUI(actorId) {
    const actor = gameState.players[actorId];
    const actorLabel = document.getElementById('actorLabel').querySelector('span');
    actorLabel.textContent = actor ? actor.username : 'Unknown';
    
    // Update who's the actor
    Object.entries(gameState.players).forEach(([id, player]) => {
        player.isActor = id === actorId;
    });
    
    const actorVideo = document.getElementById('actorVideo');
    
    // Set actor's video on the big screen
    if (actorId === gameState.userId) {
        // We are the actor - show our own video
        actorVideo.srcObject = gameState.localStream;
    } else {
        // Someone else is the actor - show their video
        if (gameState.remoteStreams && gameState.remoteStreams[actorId]) {
            actorVideo.srcObject = gameState.remoteStreams[actorId];
        } else if (gameState.peerConnections[actorId]) {
            const pc = gameState.peerConnections[actorId];
            const receivers = pc.getReceivers();
            if (receivers.length > 0) {
                const stream = new MediaStream();
                receivers.forEach(receiver => {
                    if (receiver.track) {
                        stream.addTrack(receiver.track);
                    }
                });
                if (stream.getTracks().length > 0) {
                    actorVideo.srcObject = stream;
                }
            }
        }
    }
    
    // Update the participants grid to highlight the actor
    updateParticipantsGrid();
}

function addChatMessage(sender, message, isGuess = true) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    
    if (sender === 'system') {
        div.className = 'chat-message system';
        div.innerHTML = `<span class="message">${message}</span>`;
    } else if (sender === 'correct') {
        div.className = 'chat-message correct';
        div.innerHTML = `<span class="message">${message}</span>`;
    } else if (sender === 'hint') {
        div.className = 'chat-message hint';
        div.innerHTML = `<span class="message">${message}</span>`;
    } else {
        div.className = 'chat-message';
        div.innerHTML = `
            <span class="sender">${sender}:</span>
            <span class="message">${message}</span>
        `;
    }
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showNotification(message, type = 'info') {
    // Simple notification
    const notif = document.createElement('div');
    notif.className = `notification ${type}`;
    notif.textContent = message;
    document.body.appendChild(notif);
    
    setTimeout(() => notif.classList.add('show'), 10);
    setTimeout(() => {
        notif.classList.remove('show');
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

// =============================================================================
// Timer
// =============================================================================

function startTimer(seconds) {
    gameState.timeRemaining = seconds;
    const timerBar = document.getElementById('timerBar');
    const timerText = document.getElementById('timerText');
    
    timerBar.style.width = '100%';
    timerText.textContent = seconds;
    
    gameState.timerInterval = setInterval(() => {
        gameState.timeRemaining--;
        timerText.textContent = gameState.timeRemaining;
        timerBar.style.width = (gameState.timeRemaining / seconds * 100) + '%';
        
        if (gameState.timeRemaining <= 10) {
            timerBar.classList.add('warning');
        }
        
        if (gameState.timeRemaining <= 0) {
            stopTimer();
            gameState.socket.emit('time-up', {
                roomCode: gameState.roomCode
            });
        }
    }, 1000);
}

function stopTimer() {
    if (gameState.timerInterval) {
        clearInterval(gameState.timerInterval);
        gameState.timerInterval = null;
    }
    document.getElementById('timerBar').classList.remove('warning');
}

// =============================================================================
// Cleanup
// =============================================================================
// Connection Health Check
// =============================================================================

let connectionCheckInterval = null;

function startConnectionHealthCheck() {
    // Clear any existing interval
    if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
    }
    
    // Check connections every 5 seconds
    connectionCheckInterval = setInterval(() => {
        if (!gameState.roomCode || Object.keys(gameState.players).length <= 1) return;
        
        console.log('Checking connection health...');
        
        Object.keys(gameState.players).forEach(playerId => {
            if (playerId === gameState.userId) return;
            
            const pc = gameState.peerConnections[playerId];
            
            // If no connection exists or connection failed, try to reconnect
            if (!pc || pc.connectionState === 'failed' || pc.connectionState === 'disconnected' || pc.connectionState === 'closed') {
                console.log(`Reconnecting to ${playerId} (state: ${pc ? pc.connectionState : 'none'})`);
                delete gameState.peerConnections[playerId];
                initiateConnection(playerId);
            }
        });
        
        // Update participants grid to refresh video states
        if (gameState.gameStarted) {
            updateParticipantsGrid();
        }
    }, 5000);
}

function stopConnectionHealthCheck() {
    if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
        connectionCheckInterval = null;
    }
}

// =============================================================================

function cleanup() {
    stopTimer();
    stopConnectionHealthCheck();
    
    // Close peer connections
    Object.values(gameState.peerConnections).forEach(pc => pc.close());
    gameState.peerConnections = {};
    
    // Clear remote streams
    gameState.remoteStreams = {};
    
    // Stop local stream
    if (gameState.localStream) {
        gameState.localStream.getTracks().forEach(track => track.stop());
        gameState.localStream = null;
    }
    
    // Reset state
    gameState.players = {};
    gameState.roomCode = null;
    gameState.gameStarted = false;
    gameState.isActor = false;
    gameState.currentWord = null;
    
    // Hide overlays
    document.getElementById('wordRevealOverlay').classList.add('hidden');
    document.getElementById('gameOverOverlay').classList.add('hidden');
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (gameState.roomCode) {
        gameState.socket.emit('leave-game', {
            roomCode: gameState.roomCode,
            userId: gameState.userId
        });
    }
    cleanup();
});

/**
 * Multi-User Video Call Application
 * Features: WebRTC video calling with multiple participants
 */

// Global variables
let socket = null;
let localStream = null;
let currentRoomCode = null;
let currentUserId = null;

// Store peer connections for each user
const peerConnections = {};
const remoteStreams = {};

// DOM Elements
const setupPanel = document.getElementById('setupPanel');
const waitingPanel = document.getElementById('waitingPanel');
const callPanel = document.getElementById('callPanel');

const createRoomBtn = document.getElementById('createRoomBtn');
const joinRoomBtn = document.getElementById('joinRoomBtn');
const roomCodeInput = document.getElementById('roomCodeInput');
const endCallBtn = document.getElementById('endCallBtn');
const toggleVideoBtn = document.getElementById('toggleVideoBtn');
const toggleAudioBtn = document.getElementById('toggleAudioBtn');

const localVideo = document.getElementById('localVideo');
const videoGrid = document.getElementById('videoGrid');
const videoStatus = document.getElementById('videoStatus');
const participantCount = document.getElementById('participantCount');

// ICE Server Configuration
const ICE_SERVERS = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
        { urls: 'stun:stun2.l.google.com:19302' }
    ]
};

/**
 * Initialize the application
 */
async function init() {
    console.log('Initializing Multi-User Video Call...');
    
    // Generate unique user ID
    currentUserId = `user_${Math.random().toString(36).substr(2, 9)}`;
    
    // Initialize Socket.IO
    initializeSocketIO();
    
    // Attach event listeners
    attachEventListeners();
    
    console.log('Initialization complete! User ID:', currentUserId);
}

/**
 * Initialize Socket.IO connection
 */
function initializeSocketIO() {
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to server');
    });
    
    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        videoStatus.textContent = 'Disconnected';
    });
    
    // When we get the list of users already in the room
    socket.on('room-users', async (data) => {
        console.log('Users in room:', data.users);
        updateParticipantCount();
        
        // Create offers to all existing users
        for (const userId of data.users) {
            if (userId !== currentUserId) {
                await createPeerConnection(userId);
                await createOffer(userId);
            }
        }
    });
    
    // When a new user joins
    socket.on('user-joined', async (data) => {
        console.log('User joined:', data.userId);
        videoStatus.textContent = 'New user joined';
        updateParticipantCount();
        
        // Create peer connection for new user (they will send us an offer)
        await createPeerConnection(data.userId);
    });
    
    // When a user leaves
    socket.on('user-left', (data) => {
        console.log('User left:', data.userId);
        videoStatus.textContent = 'User disconnected';
        
        // Clean up peer connection
        removePeerConnection(data.userId);
        updateParticipantCount();
    });
    
    // WebRTC signaling
    socket.on('offer', async (data) => {
        console.log('Received offer from:', data.userId);
        await handleOffer(data.offer, data.userId);
    });
    
    socket.on('answer', async (data) => {
        console.log('Received answer from:', data.userId);
        await handleAnswer(data.answer, data.userId);
    });
    
    socket.on('ice-candidate', async (data) => {
        console.log('Received ICE candidate from:', data.userId);
        await handleIceCandidate(data.candidate, data.userId);
    });
}

/**
 * Attach event listeners to buttons
 */
function attachEventListeners() {
    createRoomBtn.addEventListener('click', createRoom);
    joinRoomBtn.addEventListener('click', joinRoom);
    endCallBtn.addEventListener('click', endCall);
    toggleVideoBtn.addEventListener('click', toggleVideo);
    toggleAudioBtn.addEventListener('click', toggleAudio);
    
    // Copy room code button
    const copyBtn = document.getElementById('copyRoomCodeBtn');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(currentRoomCode);
            copyBtn.textContent = '✅';
            setTimeout(() => copyBtn.textContent = '📋', 2000);
        });
    }
    
    // Cancel waiting button
    const cancelBtn = document.getElementById('cancelWaitingBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', endCall);
    }
    
    // Auto-format room code input
    roomCodeInput.addEventListener('input', (e) => {
        let value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
        if (value.length > 4) {
            value = value.substr(0, 4) + '-' + value.substr(4, 4);
        }
        e.target.value = value;
    });
}

/**
 * Create a new video call room
 */
async function createRoom() {
    try {
        createRoomBtn.disabled = true;
        createRoomBtn.textContent = 'Creating...';
        
        // Call API to create room
        const response = await fetch('/api/call/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentRoomCode = data.data.room_code;
            
            // Setup local video stream
            await setupLocalStream();
            
            // Join the socket room
            socket.emit('join-room', {
                roomCode: currentRoomCode,
                userId: currentUserId
            });
            
            // Show waiting panel
            showPanel('waiting');
            document.getElementById('waitingRoomCode').textContent = currentRoomCode;
            document.getElementById('roomCodeDisplay').textContent = currentRoomCode;
            
        } else {
            alert('Failed to create room: ' + data.message);
        }
    } catch (error) {
        console.error('Error creating room:', error);
        alert('Error creating room. Please try again.');
    } finally {
        createRoomBtn.disabled = false;
        createRoomBtn.innerHTML = '<span class="btn__icon">🎥</span> Create Room';
    }
}

/**
 * Join an existing video call room
 */
async function joinRoom() {
    const roomCode = roomCodeInput.value.trim();
    
    if (!roomCode || roomCode.length < 8) {
        alert('Please enter a valid room code (XXXX-XXXX)');
        return;
    }
    
    try {
        joinRoomBtn.disabled = true;
        joinRoomBtn.textContent = 'Joining...';
        
        currentRoomCode = roomCode;
        
        // Setup local video stream
        await setupLocalStream();
        
        // Join the socket room
        socket.emit('join-room', {
            roomCode: currentRoomCode,
            userId: currentUserId
        });
        
        // Show call panel
        showPanel('call');
        document.getElementById('activeRoomCode').textContent = currentRoomCode;
        
    } catch (error) {
        console.error('Error joining room:', error);
        alert('Error joining room. Please try again.');
    } finally {
        joinRoomBtn.disabled = false;
        joinRoomBtn.innerHTML = '<span class="btn__icon">🚪</span> Join Room';
    }
}

/**
 * Setup local video stream (camera access)
 */
async function setupLocalStream() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({
            video: { 
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: true
        });
        
        localVideo.srcObject = localStream;
        console.log('Local stream setup complete');
        
    } catch (error) {
        console.error('Error accessing camera/microphone:', error);
        alert('Please allow camera and microphone access to continue.');
        throw error;
    }
}

/**
 * Create WebRTC peer connection for a specific user
 */
async function createPeerConnection(userId) {
    if (peerConnections[userId]) {
        console.log('Peer connection already exists for:', userId);
        return peerConnections[userId];
    }
    
    console.log('Creating peer connection for:', userId);
    
    const pc = new RTCPeerConnection(ICE_SERVERS);
    peerConnections[userId] = pc;
    
    // Add local stream tracks to peer connection
    if (localStream) {
        localStream.getTracks().forEach(track => {
            pc.addTrack(track, localStream);
        });
    }
    
    // Handle incoming remote stream
    pc.ontrack = (event) => {
        console.log('Received remote track from:', userId);
        
        if (!remoteStreams[userId]) {
            remoteStreams[userId] = event.streams[0];
            addVideoElement(userId, event.streams[0]);
        }
        
        videoStatus.textContent = 'Connected';
        
        // If we're still in waiting panel, switch to call panel
        if (waitingPanel.style.display !== 'none') {
            showPanel('call');
            document.getElementById('activeRoomCode').textContent = currentRoomCode;
        }
    };
    
    // Handle ICE candidates
    pc.onicecandidate = (event) => {
        if (event.candidate) {
            socket.emit('ice-candidate', {
                roomCode: currentRoomCode,
                candidate: event.candidate,
                userId: currentUserId,
                targetUserId: userId
            });
        }
    };
    
    // Handle connection state changes
    pc.onconnectionstatechange = () => {
        console.log(`Connection state with ${userId}:`, pc.connectionState);
        
        if (pc.connectionState === 'connected') {
            videoStatus.textContent = 'Connected';
        } else if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
            removePeerConnection(userId);
        }
    };
    
    return pc;
}

/**
 * Remove peer connection and associated video element
 */
function removePeerConnection(userId) {
    // Close peer connection
    if (peerConnections[userId]) {
        peerConnections[userId].close();
        delete peerConnections[userId];
    }
    
    // Remove remote stream
    if (remoteStreams[userId]) {
        delete remoteStreams[userId];
    }
    
    // Remove video element
    const videoContainer = document.getElementById(`video-container-${userId}`);
    if (videoContainer) {
        videoContainer.remove();
    }
    
    updateParticipantCount();
}

/**
 * Add video element for a remote user
 */
function addVideoElement(userId, stream) {
    // Check if video element already exists
    if (document.getElementById(`video-container-${userId}`)) {
        return;
    }
    
    const container = document.createElement('div');
    container.className = 'video-item';
    container.id = `video-container-${userId}`;
    
    const video = document.createElement('video');
    video.id = `video-${userId}`;
    video.autoplay = true;
    video.playsInline = true;
    video.srcObject = stream;
    
    const label = document.createElement('div');
    label.className = 'video-label';
    label.textContent = `User ${userId.substr(-4)}`;
    
    container.appendChild(video);
    container.appendChild(label);
    videoGrid.appendChild(container);
    
    updateParticipantCount();
}

/**
 * Update participant count display
 */
function updateParticipantCount() {
    const count = Object.keys(peerConnections).length + 1; // +1 for local user
    if (participantCount) {
        participantCount.textContent = `${count} participant${count !== 1 ? 's' : ''}`;
    }
}

/**
 * Create WebRTC offer for a specific user
 */
async function createOffer(userId) {
    try {
        const pc = peerConnections[userId];
        if (!pc) {
            console.error('No peer connection for:', userId);
            return;
        }
        
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        
        socket.emit('offer', {
            roomCode: currentRoomCode,
            offer: offer,
            userId: currentUserId,
            targetUserId: userId
        });
        
        console.log('Offer sent to:', userId);
    } catch (error) {
        console.error('Error creating offer:', error);
    }
}

/**
 * Handle incoming WebRTC offer
 */
async function handleOffer(offer, userId) {
    try {
        let pc = peerConnections[userId];
        if (!pc) {
            pc = await createPeerConnection(userId);
        }
        
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        
        socket.emit('answer', {
            roomCode: currentRoomCode,
            answer: answer,
            userId: currentUserId,
            targetUserId: userId
        });
        
        console.log('Answer sent to:', userId);
    } catch (error) {
        console.error('Error handling offer:', error);
    }
}

/**
 * Handle incoming WebRTC answer
 */
async function handleAnswer(answer, userId) {
    try {
        const pc = peerConnections[userId];
        if (pc) {
            await pc.setRemoteDescription(new RTCSessionDescription(answer));
            console.log('Answer processed from:', userId);
        }
    } catch (error) {
        console.error('Error handling answer:', error);
    }
}

/**
 * Handle incoming ICE candidate
 */
async function handleIceCandidate(candidate, userId) {
    try {
        const pc = peerConnections[userId];
        if (pc) {
            await pc.addIceCandidate(new RTCIceCandidate(candidate));
            console.log('ICE candidate added from:', userId);
        }
    } catch (error) {
        console.error('Error adding ICE candidate:', error);
    }
}

/**
 * Toggle video on/off
 */
function toggleVideo() {
    if (localStream) {
        const videoTrack = localStream.getVideoTracks()[0];
        if (videoTrack) {
            videoTrack.enabled = !videoTrack.enabled;
            toggleVideoBtn.classList.toggle('control-btn--off', !videoTrack.enabled);
            toggleVideoBtn.querySelector('.control-btn__icon').textContent = videoTrack.enabled ? '📹' : '🚫';
        }
    }
}

/**
 * Toggle audio on/off
 */
function toggleAudio() {
    if (localStream) {
        const audioTrack = localStream.getAudioTracks()[0];
        if (audioTrack) {
            audioTrack.enabled = !audioTrack.enabled;
            toggleAudioBtn.classList.toggle('control-btn--off', !audioTrack.enabled);
            toggleAudioBtn.querySelector('.control-btn__icon').textContent = audioTrack.enabled ? '🎤' : '🔇';
        }
    }
}

/**
 * End the call
 */
async function endCall() {
    try {
        // Stop all tracks
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
        }
        
        // Close all peer connections
        for (const userId of Object.keys(peerConnections)) {
            removePeerConnection(userId);
        }
        
        // Clear video grid (except local video container)
        const videoItems = videoGrid.querySelectorAll('.video-item');
        videoItems.forEach(item => item.remove());
        
        // Leave socket room
        if (socket && currentRoomCode) {
            socket.emit('leave-room', {
                roomCode: currentRoomCode,
                userId: currentUserId
            });
        }
        
        // Call API to end call
        if (currentRoomCode) {
            await fetch(`/api/call/${currentRoomCode}/end`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        // Reset state
        currentRoomCode = null;
        
        // Reset local video
        localVideo.srcObject = null;
        
        // Show setup panel
        showPanel('setup');
        
    } catch (error) {
        console.error('Error ending call:', error);
    }
}

/**
 * Show specific panel
 */
function showPanel(panel) {
    setupPanel.style.display = 'none';
    waitingPanel.style.display = 'none';
    callPanel.style.display = 'none';
    
    switch(panel) {
        case 'setup':
            setupPanel.style.display = 'flex';
            break;
        case 'waiting':
            waitingPanel.style.display = 'flex';
            break;
        case 'call':
            callPanel.style.display = 'flex';
            break;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);

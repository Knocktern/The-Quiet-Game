"""
Sign Language Guessing Game - Main Application Entry Point.

A Skribbl-like game where players guess words from sign language.
One player acts out words using sign language via video,
while others try to guess the word.

Run with: python app.py
Access at: http://localhost:5000
"""

import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room

from config import get_config, DevelopmentConfig
from models.database import init_db, set_database_path
from routes import videocall_bp
from routes.game import game_bp
from services.game_logic import (
    create_game, get_game, remove_game, GameState
)
from services.word_bank import get_words_for_selection


# =============================================================================
# Application Factory
# =============================================================================

def create_app(config_name: str = 'development') -> Flask:
    """
    Application factory function.
    
    Creates and configures the Flask application with all necessary
    extensions, blueprints, and initialization.
    
    Args:
        config_name: Configuration environment name.
                    Options: 'development', 'production', 'testing'
    
    Returns:
        Configured Flask application instance.
    """
    # Initialize Flask app
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Ensure instance folder exists
    instance_path = os.path.join(app.root_path, 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    # Initialize database
    set_database_path(config.DATABASE_PATH)
    init_db()
    
    # Register blueprints (only videocall now)
    app.register_blueprint(videocall_bp)
    app.register_blueprint(game_bp)
    
    # Register main routes
    register_main_routes(app)
    
    return app


def register_main_routes(app: Flask) -> None:
    """
    Register main application routes.
    
    Args:
        app: Flask application instance.
    """
    
    @app.route('/')
    def index():
        """Render the landing page."""
        return render_template('index.html')
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return render_template('base.html', error="Page not found"), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """Handle 500 errors."""
        return render_template('base.html', error="Server error"), 500


# =============================================================================
# Create Application and SocketIO
# =============================================================================

app = create_app('development')
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading'
)


# =============================================================================
# SocketIO Event Handlers for Real-time Communication
# =============================================================================

# Store connected users per room
connected_users: dict = {}


@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection."""
    print(f"Client connected")
    emit('connected', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    print("Client disconnected")


# =============================================================================
# Game Room Handlers
# =============================================================================

@socketio.on('join-game')
def handle_join_game(data: dict):
    """
    Handle user joining a game room.
    Supports joining mid-game - player will be added and synced with current round.
    """
    room_code = data.get('roomCode', '').upper()
    user_id = data.get('userId', '')
    username = data.get('username', f'Player_{user_id[-4:]}')
    
    if not room_code or not user_id:
        emit('error', {'message': 'Room code and user ID are required'})
        return
    
    # Join the SocketIO room
    join_room(room_code)
    
    # Track connected user
    if room_code not in connected_users:
        connected_users[room_code] = {}
    
    connected_users[room_code][user_id] = {
        'username': username,
        'userId': user_id
    }
    
    # Get or create game
    game = get_game(room_code)
    if not game:
        game = create_game(room_code)
    
    # Add player to game
    game.add_player(user_id, username)
    
    # Check if game is already in progress (mid-game join)
    is_mid_game_join = game.game_started and not game.game_ended
    
    # Send current game state to the new player
    game_state = game.get_game_state()
    game_state['is_mid_game_join'] = is_mid_game_join
    emit('game-state', game_state)
    
    # Notify others that a new user joined
    emit('player-joined', {
        'userId': user_id,
        'username': username,
        'gameState': game.get_game_state(),
        'isMidGameJoin': is_mid_game_join
    }, room=room_code, include_self=False)
    
    join_type = "mid-game" if is_mid_game_join else "lobby"
    print(f"User {username} joined game {room_code} ({join_type}). Total players: {len(game.players)}")


@socketio.on('leave-game')
def handle_leave_game(data: dict):
    """Handle user leaving a game room."""
    room_code = data.get('roomCode', '').upper()
    user_id = data.get('userId', '')
    
    if room_code and user_id:
        leave_room(room_code)
        
        game = get_game(room_code)
        if game:
            game.remove_player(user_id)
            
            if len(game.players) == 0:
                remove_game(room_code)
            else:
                emit('player-left', {
                    'userId': user_id,
                    'gameState': game.get_game_state()
                }, room=room_code)
        
        if room_code in connected_users and user_id in connected_users[room_code]:
            del connected_users[room_code][user_id]
            if not connected_users[room_code]:
                del connected_users[room_code]
        
        print(f"User {user_id} left game {room_code}")


@socketio.on('player-ready')
def handle_player_ready(data: dict):
    """Handle player ready status."""
    room_code = data.get('roomCode', '').upper()
    user_id = data.get('userId', '')
    is_ready = data.get('isReady', True)
    
    game = get_game(room_code)
    if game:
        game.set_player_ready(user_id, is_ready)
        
        emit('player-ready-update', {
            'userId': user_id,
            'isReady': is_ready,
            'allReady': game.all_players_ready(),
            'gameState': game.get_game_state()
        }, room=room_code)


@socketio.on('start-game')
def handle_start_game(data: dict):
    """Handle game start request."""
    room_code = data.get('roomCode', '').upper()
    difficulty = data.get('difficulty', 'easy')
    
    game = get_game(room_code)
    if not game:
        emit('error', {'message': 'Game not found'})
        return
    
    if not game.can_start_game():
        emit('error', {'message': 'Need at least 2 players to start'})
        return
    
    game.difficulty = difficulty
    game.start_game()
    
    # Get word choices for the first actor
    word_choices = get_words_for_selection(difficulty, 3)
    actor_id = game.get_current_actor()
    
    emit('game-started', {
        'gameState': game.get_game_state(),
        'actorId': actor_id
    }, room=room_code)
    
    # Send word choices only to the actor
    emit('word-choices', {
        'words': word_choices
    }, room=room_code)  # Will filter client-side
    
    print(f"Game started in room {room_code}")


@socketio.on('select-word')
def handle_select_word(data: dict):
    """Handle actor selecting a word."""
    room_code = data.get('roomCode', '').upper()
    user_id = data.get('userId', '')
    word_data = data.get('word', {})
    
    game = get_game(room_code)
    if not game:
        return
    
    # Verify this user is the current actor
    if game.get_current_actor() != user_id:
        emit('error', {'message': 'Not your turn to act'})
        return
    
    # Start the round
    game.start_new_round(word_data)
    
    # Notify all players (but don't reveal the word to guessers)
    emit('round-started', {
        'roundNumber': game.current_round.round_number,
        'actorId': user_id,
        'category': word_data['category'],
        'wordLength': len(word_data['word']),
        'difficulty': word_data.get('difficulty', 'easy')
    }, room=room_code)
    
    # Send the actual word only to the actor
    emit('your-word', {
        'word': word_data['word'],
        'category': word_data['category']
    }, room=room_code)  # Will filter client-side
    
    print(f"Round {game.current_round.round_number} started in {room_code}: {word_data['word']}")


@socketio.on('submit-guess')
def handle_submit_guess(data: dict):
    """Handle a player's guess."""
    room_code = data.get('roomCode', '').upper()
    user_id = data.get('userId', '')
    guess = data.get('guess', '').strip()
    
    if not guess:
        return
    
    game = get_game(room_code)
    if not game or not game.current_round:
        return
    
    result = game.submit_guess(user_id, guess)
    username = game.players[user_id].username if user_id in game.players else 'Unknown'
    
    # Broadcast the guess to everyone (but not if correct - that reveals the answer)
    if not result['correct']:
        emit('guess-made', {
            'userId': user_id,
            'username': username,
            'guess': guess
        }, room=room_code)
    else:
        # Correct guess!
        emit('correct-guess', {
            'userId': user_id,
            'username': username,
            'points': result['points'],
            'leaderboard': game.get_leaderboard()
        }, room=room_code)
        
        # Check if everyone has guessed correctly
        guessers = [p for p in game.players.values() 
                   if p.user_id != game.current_round.actor_id]
        all_guessed = all(p.has_guessed_correctly for p in guessers)
        
        if all_guessed:
            end_current_round(room_code)


@socketio.on('request-hint')
def handle_request_hint(data: dict):
    """Handle hint request."""
    room_code = data.get('roomCode', '').upper()
    
    game = get_game(room_code)
    if game and game.current_round:
        hint = game.use_hint()
        if hint:
            emit('hint', {'hint': hint}, room=room_code)


@socketio.on('time-up')
def handle_time_up(data: dict):
    """Handle round time expiration."""
    room_code = data.get('roomCode', '').upper()
    end_current_round(room_code)


def end_current_round(room_code: str):
    """End the current round and prepare for next."""
    game = get_game(room_code)
    if not game or not game.current_round:
        return
    
    word = game.current_round.word
    round_summary = game.end_round()
    
    emit('round-ended', {
        'word': word,
        'summary': round_summary,
        'gameState': game.get_game_state(),
        'gameEnded': game.game_ended
    }, room=room_code)
    
    if game.game_ended:
        emit('game-over', {
            'results': game.get_final_results()
        }, room=room_code)
    else:
        # Send word choices for next round
        word_choices = get_words_for_selection(game.difficulty, 3)
        actor_id = game.get_current_actor()
        
        emit('next-round', {
            'actorId': actor_id,
            'words': word_choices,
            'gameState': game.get_game_state()
        }, room=room_code)


@socketio.on('chat-message')
def handle_chat_message(data: dict):
    """Handle chat messages (non-guess messages)."""
    room_code = data.get('roomCode', '').upper()
    user_id = data.get('userId', '')
    message = data.get('message', '').strip()
    
    if not message:
        return
    
    game = get_game(room_code)
    username = 'Unknown'
    if game and user_id in game.players:
        username = game.players[user_id].username
    
    emit('chat-message', {
        'userId': user_id,
        'username': username,
        'message': message
    }, room=room_code)


# =============================================================================
# WebRTC Signaling Handlers (for video)
# =============================================================================

@socketio.on('offer')
def handle_offer(data: dict):
    """Handle WebRTC offer for peer connection."""
    if not data or not isinstance(data, dict):
        return
    
    room_code = (data.get('roomCode') or '').upper()
    offer = data.get('offer')
    user_id = data.get('userId')
    target_id = data.get('targetId')
    
    if not all([room_code, offer, user_id]):
        return
    
    emit('offer', {
        'offer': offer,
        'userId': user_id,
        'targetId': target_id
    }, room=room_code, include_self=False)


@socketio.on('answer')
def handle_answer(data: dict):
    """Handle WebRTC answer for peer connection."""
    if not data or not isinstance(data, dict):
        return
    
    room_code = (data.get('roomCode') or '').upper()
    answer = data.get('answer')
    user_id = data.get('userId')
    target_id = data.get('targetId')
    
    if not all([room_code, answer, user_id]):
        return
    
    emit('answer', {
        'answer': answer,
        'userId': user_id,
        'targetId': target_id
    }, room=room_code, include_self=False)


@socketio.on('ice-candidate')
def handle_ice_candidate(data: dict):
    """Handle ICE candidate exchange for WebRTC."""
    if not data or not isinstance(data, dict):
        return
    
    room_code = (data.get('roomCode') or '').upper()
    candidate = data.get('candidate')
    user_id = data.get('userId')
    target_id = data.get('targetId')
    
    if not room_code or not candidate:
        return
    
    emit('ice-candidate', {
        'candidate': candidate,
        'userId': user_id,
        'targetId': target_id
    }, room=room_code, include_self=False)


# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║              🤫 The Quiet Game 🤫                             ║
    ║                                                               ║
    ║    A Skribbl-like game using sign language!                   ║
    ║    Act out words with signs, others guess.                    ║
    ║                                                               ║
    ║    Server running at: http://localhost:5000                   ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True
    )

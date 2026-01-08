"""
Game Routes for Sign Language Guessing Game.

Handles HTTP routes for game creation and page rendering.
"""

from flask import Blueprint, render_template, request, jsonify
import random
import string


# Create blueprint
game_bp = Blueprint('game', __name__, url_prefix='/game')


def generate_room_code() -> str:
    """Generate a unique room code in format XXXX-XXXX."""
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choices(chars, k=4))
    part2 = ''.join(random.choices(chars, k=4))
    return f"{part1}-{part2}"


@game_bp.route('/')
def game_page():
    """Render the main game page."""
    return render_template('game.html')


@game_bp.route('/create', methods=['POST'])
def create_game_room():
    """
    Create a new game room.
    
    Returns:
        JSON with room_code
    """
    room_code = generate_room_code()
    
    return jsonify({
        'success': True,
        'room_code': room_code
    })


@game_bp.route('/join/<room_code>')
def join_game_room(room_code: str):
    """
    Join an existing game room.
    
    Args:
        room_code: The room code to join
        
    Returns:
        Rendered game template
    """
    return render_template('game.html', room_code=room_code.upper())


@game_bp.route('/validate/<room_code>')
def validate_room(room_code: str):
    """
    Validate if a room exists.
    
    Args:
        room_code: The room code to validate
        
    Returns:
        JSON with validation result
    """
    from services.game_logic import get_game
    
    game = get_game(room_code.upper())
    
    return jsonify({
        'valid': game is not None,
        'players': len(game.players) if game else 0
    })

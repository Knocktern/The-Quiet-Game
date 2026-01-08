"""
Video Call Routes for Multi-User Video Conference.

This module contains routes for the video call functionality.
Users can create video call rooms, join existing rooms, and 
participate in multi-user video conferences via WebRTC and SocketIO.

Routes:
    GET  /call              - Render video call page (create new room)
    GET  /call/<room_code>  - Render video call page (join existing room)
    POST /api/call/create   - Create new video call room
    POST /api/call/<code>/end  - End the video call
"""

from flask import Blueprint, render_template, request, jsonify
from typing import Dict, Any

from models.session import (
    create_video_call,
    get_video_call_by_room,
    end_video_call
)


# Create Blueprint for video call routes
videocall_bp = Blueprint(
    'videocall',
    __name__,
    url_prefix=''
)


# =============================================================================
# Page Routes
# =============================================================================

@videocall_bp.route('/call')
def call_page() -> str:
    """
    Render the video call page for creating a new room.
    
    Returns:
        Rendered HTML template for video call interface.
    """
    return render_template('videocall.html', room_code=None)


@videocall_bp.route('/call/<room_code>')
def join_call_page(room_code: str) -> str:
    """
    Render the video call page for joining an existing room.
    
    Args:
        room_code: The room code to join.
        
    Returns:
        Rendered HTML template with room code pre-filled.
    """
    return render_template(
        'videocall.html',
        room_code=room_code.upper()
    )


# =============================================================================
# API Routes
# =============================================================================

@videocall_bp.route('/api/call/create', methods=['POST'])
def create_call_room() -> tuple:
    """
    Create a new video call room.
    
    Generates a unique room code that can be shared with other users
    to establish peer-to-peer video connections.
    
    Returns:
        JSON response with room details including shareable code.
    """
    try:
        # Create new video call room
        call = create_video_call()
        
        return jsonify({
            'success': True,
            'message': 'Video call room created successfully',
            'data': {
                'room_code': call['room_code'],
                'start_time': call['start_time'],
                'share_url': f"/call/{call['room_code']}"
            }
        }), 201
        
    except Exception as error:
        print(f"Error creating call room: {error}")
        return jsonify({
            'success': False,
            'message': 'Failed to create video call room',
            'data': None
        }), 500


@videocall_bp.route('/api/call/<room_code>/end', methods=['POST'])
def end_call(room_code: str) -> tuple:
    """
    End a video call.
    
    Marks the call as ended.
    
    Args:
        room_code: The room code.
        
    Returns:
        JSON response with call end confirmation.
    """
    try:
        call = end_video_call(room_code)
        
        if not call:
            return jsonify({
                'success': False,
                'message': 'Video call room not found',
                'data': None
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Video call ended successfully',
            'data': {
                'room_code': call['room_code'],
                'start_time': call['start_time'],
                'end_time': call['end_time']
            }
        }), 200
        
    except Exception as error:
        print(f"Error ending call: {error}")
        return jsonify({
            'success': False,
            'message': 'Failed to end video call',
            'data': None
        }), 500

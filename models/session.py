"""
Session and data models for Silent Mood Messenger.

This module contains functions for CRUD operations on sessions, guesses,
and video calls. All functions use proper error handling and type hints.
"""

import json
import random
import string
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List, Any

from models.database import db_transaction, get_db_connection, close_db_connection


# Session code configuration
SESSION_CODE_LENGTH: int = 6
SESSION_CODE_CHARS: str = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_session_code() -> str:
    """
    Generate a unique 6-character alphanumeric session code.
    
    Uses characters that are visually distinct (excludes I, O, 0, 1)
    to prevent user confusion when sharing codes.
    
    Returns:
        A unique 6-character uppercase alphanumeric code.
    """
    return ''.join(random.choices(SESSION_CODE_CHARS, k=SESSION_CODE_LENGTH))


def generate_room_code() -> str:
    """
    Generate a unique room code for video calls.
    
    Format: XXXX-XXXX for easy sharing and readability.
    
    Returns:
        An 8-character room code with hyphen separator.
    """
    part1 = ''.join(random.choices(SESSION_CODE_CHARS, k=4))
    part2 = ''.join(random.choices(SESSION_CODE_CHARS, k=4))
    return f"{part1}-{part2}"


# =============================================================================
# Session Operations (Feature 1: Encoder)
# =============================================================================

def create_session(emotion: str, pattern_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new emotion encoding session.
    
    Args:
        emotion: The emotion being encoded (e.g., 'happy', 'sad').
        pattern_config: Dictionary containing visual pattern configuration.
    
    Returns:
        Dictionary containing session details including the unique code.
    
    Raises:
        sqlite3.Error: If database operation fails.
        ValueError: If emotion or pattern_config is invalid.
    """
    if not emotion or not isinstance(emotion, str):
        raise ValueError("Emotion must be a non-empty string")
    
    if not pattern_config or not isinstance(pattern_config, dict):
        raise ValueError("Pattern config must be a non-empty dictionary")
    
    session_code = generate_session_code()
    pattern_json = json.dumps(pattern_config)
    
    with db_transaction() as connection:
        cursor = connection.cursor()
        
        # Ensure unique session code (retry if collision)
        max_retries = 5
        for attempt in range(max_retries):
            try:
                cursor.execute(
                    """
                    INSERT INTO sessions (session_code, emotion, pattern_config)
                    VALUES (?, ?, ?)
                    """,
                    (session_code, emotion.lower(), pattern_json)
                )
                break
            except sqlite3.IntegrityError:
                if attempt < max_retries - 1:
                    session_code = generate_session_code()
                else:
                    raise sqlite3.Error("Failed to generate unique session code")
        
        session_id = cursor.lastrowid
    
    return {
        'id': session_id,
        'session_code': session_code,
        'emotion': emotion.lower(),
        'pattern_config': pattern_config,
        'created_at': datetime.now().isoformat()
    }


def get_session_by_code(session_code: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a session by its unique code.
    
    Args:
        session_code: The 6-character session code.
    
    Returns:
        Dictionary containing session details, or None if not found.
    """
    if not session_code:
        return None
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, session_code, emotion, pattern_config, created_at
            FROM sessions
            WHERE session_code = ?
            """,
            (session_code.upper(),)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row['id'],
                'session_code': row['session_code'],
                'emotion': row['emotion'],
                'pattern_config': json.loads(row['pattern_config']),
                'created_at': row['created_at']
            }
        return None
    finally:
        close_db_connection(connection)


def get_session_by_id(session_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a session by its database ID.
    
    Args:
        session_id: The session's database ID.
    
    Returns:
        Dictionary containing session details, or None if not found.
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, session_code, emotion, pattern_config, created_at
            FROM sessions
            WHERE id = ?
            """,
            (session_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row['id'],
                'session_code': row['session_code'],
                'emotion': row['emotion'],
                'pattern_config': json.loads(row['pattern_config']),
                'created_at': row['created_at']
            }
        return None
    finally:
        close_db_connection(connection)


# =============================================================================
# Guess Operations (Feature 2: Decoder)
# =============================================================================

def create_guess(session_id: int, guessed_emotion: str, score: int) -> Dict[str, Any]:
    """
    Record a decoder's guess for a session.
    
    Args:
        session_id: The ID of the session being decoded.
        guessed_emotion: The emotion guessed by the decoder.
        score: The understanding score (0-100).
    
    Returns:
        Dictionary containing the guess details.
    
    Raises:
        ValueError: If score is not between 0 and 100.
        sqlite3.Error: If the session doesn't exist.
    """
    if not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100")
    
    with db_transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO guesses (session_id, guessed_emotion, score)
            VALUES (?, ?, ?)
            """,
            (session_id, guessed_emotion.lower(), score)
        )
        guess_id = cursor.lastrowid
    
    return {
        'id': guess_id,
        'session_id': session_id,
        'guessed_emotion': guessed_emotion.lower(),
        'score': score,
        'created_at': datetime.now().isoformat()
    }


def get_guesses_for_session(session_id: int) -> List[Dict[str, Any]]:
    """
    Retrieve all guesses for a specific session.
    
    Args:
        session_id: The ID of the session.
    
    Returns:
        List of dictionaries containing guess details.
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, session_id, guessed_emotion, score, created_at
            FROM guesses
            WHERE session_id = ?
            ORDER BY created_at DESC
            """,
            (session_id,)
        )
        rows = cursor.fetchall()
        
        return [
            {
                'id': row['id'],
                'session_id': row['session_id'],
                'guessed_emotion': row['guessed_emotion'],
                'score': row['score'],
                'created_at': row['created_at']
            }
            for row in rows
        ]
    finally:
        close_db_connection(connection)


# =============================================================================
# Video Call Operations (Feature 3: Video Call)
# =============================================================================

def create_video_call() -> Dict[str, Any]:
    """
    Create a new video call room.
    
    Returns:
        Dictionary containing the room details including room code.
    """
    room_code = generate_room_code()
    
    with db_transaction() as connection:
        cursor = connection.cursor()
        
        # Ensure unique room code
        max_retries = 5
        for attempt in range(max_retries):
            try:
                cursor.execute(
                    """
                    INSERT INTO video_calls (room_code, mood_timeline)
                    VALUES (?, '[]')
                    """,
                    (room_code,)
                )
                break
            except sqlite3.IntegrityError:
                if attempt < max_retries - 1:
                    room_code = generate_room_code()
                else:
                    raise sqlite3.Error("Failed to generate unique room code")
        
        call_id = cursor.lastrowid
    
    return {
        'id': call_id,
        'room_code': room_code,
        'mood_timeline': [],
        'start_time': datetime.now().isoformat(),
        'end_time': None
    }


def get_video_call_by_room(room_code: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a video call by its room code.
    
    Args:
        room_code: The room code (format: XXXX-XXXX).
    
    Returns:
        Dictionary containing call details, or None if not found.
    """
    if not room_code:
        return None
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, room_code, mood_timeline, start_time, end_time
            FROM video_calls
            WHERE room_code = ?
            """,
            (room_code.upper(),)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row['id'],
                'room_code': row['room_code'],
                'mood_timeline': json.loads(row['mood_timeline'] or '[]'),
                'start_time': row['start_time'],
                'end_time': row['end_time']
            }
        return None
    finally:
        close_db_connection(connection)


def update_video_call_mood(room_code: str, user_id: str, emotion: str) -> Dict[str, Any]:
    """
    Add a mood update to a video call's timeline.
    
    Args:
        room_code: The room code of the call.
        user_id: Identifier for the user updating their mood.
        emotion: The new emotion being expressed.
    
    Returns:
        Dictionary containing the mood update details.
    
    Raises:
        ValueError: If the room doesn't exist.
    """
    call = get_video_call_by_room(room_code)
    if not call:
        raise ValueError(f"Video call room '{room_code}' not found")
    
    mood_update = {
        'user': user_id,
        'emotion': emotion.lower(),
        'timestamp': datetime.now().isoformat()
    }
    
    timeline = call['mood_timeline']
    timeline.append(mood_update)
    
    with db_transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE video_calls
            SET mood_timeline = ?
            WHERE room_code = ?
            """,
            (json.dumps(timeline), room_code.upper())
        )
    
    return mood_update


def end_video_call(room_code: str) -> Optional[Dict[str, Any]]:
    """
    Mark a video call as ended.
    
    Args:
        room_code: The room code of the call to end.
    
    Returns:
        Dictionary containing the final call details, or None if not found.
    """
    with db_transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE video_calls
            SET end_time = ?
            WHERE room_code = ? AND end_time IS NULL
            """,
            (datetime.now().isoformat(), room_code.upper())
        )
    
    return get_video_call_by_room(room_code)

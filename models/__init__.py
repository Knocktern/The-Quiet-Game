"""
Models package initialization.

This package contains database connection utilities and model definitions
for the Silent Mood Messenger application.
"""

from models.database import init_db, get_db_connection, close_db_connection
from models.session import (
    create_session,
    get_session_by_code,
    create_guess,
    get_guesses_for_session,
    create_video_call,
    get_video_call_by_room,
    update_video_call_mood,
    end_video_call
)

__all__ = [
    'init_db',
    'get_db_connection',
    'close_db_connection',
    'create_session',
    'get_session_by_code',
    'create_guess',
    'get_guesses_for_session',
    'create_video_call',
    'get_video_call_by_room',
    'update_video_call_mood',
    'end_video_call'
]

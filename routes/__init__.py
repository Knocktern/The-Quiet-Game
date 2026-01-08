"""
Routes package initialization.

This package contains Flask Blueprints for video call functionality only.
"""

from routes.videocall import videocall_bp

__all__ = [
    'videocall_bp'
]

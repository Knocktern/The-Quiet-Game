"""
Configuration settings for Silent Mood Messenger application.

This module contains all configuration variables used throughout the application.
Centralizing configuration ensures consistency and makes deployment easier.
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class with default settings."""
    
    # Flask Core Settings
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'silent-mood-secret-key-2026')
    DEBUG: bool = False
    TESTING: bool = False
    
    # Database Settings
    BASE_DIR: str = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH: str = os.path.join(BASE_DIR, 'instance', 'silent_mood.db')
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    
    # Session Settings
    SESSION_CODE_LENGTH: int = 6
    SESSION_CODE_CHARACTERS: str = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # Excluded I, O, 0, 1 for clarity
    
    # SocketIO Settings
    SOCKETIO_ASYNC_MODE: str = 'threading'
    
    # WebRTC Settings
    ICE_SERVERS: list = [
        {'urls': 'stun:stun.l.google.com:19302'},
        {'urls': 'stun:stun1.l.google.com:19302'}
    ]
    
    # Application Settings
    MAX_MOOD_UPDATES_PER_CALL: int = 100
    PATTERN_ANIMATION_DURATION: int = 5000  # milliseconds


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG: bool = True
    ENV: str = 'development'


class ProductionConfig(Config):
    """Production environment configuration."""
    
    DEBUG: bool = False
    ENV: str = 'production'


class TestingConfig(Config):
    """Testing environment configuration."""
    
    TESTING: bool = True
    DATABASE_PATH: str = ':memory:'


# Configuration dictionary for easy access
config_by_name: dict = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = 'default') -> Config:
    """
    Retrieve configuration class by name.
    
    Args:
        config_name: The name of the configuration to retrieve.
                    Options: 'development', 'production', 'testing', 'default'
    
    Returns:
        Configuration class corresponding to the given name.
    """
    return config_by_name.get(config_name, DevelopmentConfig)

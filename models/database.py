"""
Database connection and initialization module.

This module handles SQLite database connection management and schema initialization.
It provides utility functions for creating and managing database connections
throughout the application lifecycle.
"""

import sqlite3
import os
from typing import Optional
from contextlib import contextmanager


# Database file path - will be set from config
_database_path: Optional[str] = None


def set_database_path(path: str) -> None:
    """
    Set the database file path.
    
    Args:
        path: Absolute path to the SQLite database file.
    """
    global _database_path
    _database_path = path
    
    # Ensure the directory exists
    db_dir = os.path.dirname(path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)


def get_db_connection() -> sqlite3.Connection:
    """
    Create and return a new database connection.
    
    Returns:
        sqlite3.Connection: A new database connection with row factory set
                          to return dictionaries.
    
    Raises:
        RuntimeError: If database path has not been set.
        sqlite3.Error: If connection fails.
    """
    if _database_path is None:
        raise RuntimeError("Database path not set. Call set_database_path() first.")
    
    try:
        connection = sqlite3.connect(_database_path)
        connection.row_factory = sqlite3.Row  # Enable dict-like access to rows
        connection.execute("PRAGMA foreign_keys = ON")  # Enable foreign key support
        return connection
    except sqlite3.Error as error:
        raise sqlite3.Error(f"Failed to connect to database: {error}")


def close_db_connection(connection: sqlite3.Connection) -> None:
    """
    Safely close a database connection.
    
    Args:
        connection: The database connection to close.
    """
    if connection:
        try:
            connection.close()
        except sqlite3.Error:
            pass  # Ignore errors when closing


@contextmanager
def db_transaction():
    """
    Context manager for database transactions.
    
    Provides automatic commit on success and rollback on failure.
    
    Yields:
        sqlite3.Connection: Database connection within a transaction.
    
    Example:
        with db_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ...")
    """
    connection = get_db_connection()
    try:
        yield connection
        connection.commit()
    except Exception as error:
        connection.rollback()
        raise error
    finally:
        close_db_connection(connection)


def init_db() -> None:
    """
    Initialize the database with required tables.
    
    Creates all tables if they don't exist. This function is idempotent
    and safe to call multiple times.
    
    Tables created:
        - sessions: Stores emotion encoding sessions
        - guesses: Stores decoder guesses and scores
        - video_calls: Stores video call sessions and mood timelines
    """
    schema = """
    -- Sessions table: Stores emotion encoding sessions
    -- Each session has a unique code that users share to decode patterns
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_code TEXT UNIQUE NOT NULL,
        emotion TEXT NOT NULL,
        pattern_config TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create index for faster session code lookups
    CREATE INDEX IF NOT EXISTS idx_sessions_code ON sessions(session_code);
    
    -- Guesses table: Stores decoder attempts and understanding scores
    -- Links to sessions via foreign key for referential integrity
    CREATE TABLE IF NOT EXISTS guesses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        guessed_emotion TEXT NOT NULL,
        score INTEGER NOT NULL CHECK(score >= 0 AND score <= 100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );
    
    -- Create index for faster session-based guess lookups
    CREATE INDEX IF NOT EXISTS idx_guesses_session ON guesses(session_id);
    
    -- Video calls table: Stores video call sessions and mood updates
    -- mood_timeline is a JSON array of mood change events
    CREATE TABLE IF NOT EXISTS video_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT UNIQUE NOT NULL,
        mood_timeline TEXT DEFAULT '[]',
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP
    );
    
    -- Create index for faster room code lookups
    CREATE INDEX IF NOT EXISTS idx_video_calls_room ON video_calls(room_code);
    """
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.executescript(schema)
        connection.commit()
        print("✓ Database initialized successfully")
    except sqlite3.Error as error:
        print(f"✗ Database initialization failed: {error}")
        raise
    finally:
        close_db_connection(connection)


def reset_db() -> None:
    """
    Reset the database by dropping all tables and reinitializing.
    
    WARNING: This will delete all data. Use only for development/testing.
    """
    drop_schema = """
    DROP TABLE IF EXISTS guesses;
    DROP TABLE IF EXISTS video_calls;
    DROP TABLE IF EXISTS sessions;
    """
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.executescript(drop_schema)
        connection.commit()
        print("✓ Database tables dropped")
    except sqlite3.Error as error:
        print(f"✗ Failed to drop tables: {error}")
        raise
    finally:
        close_db_connection(connection)
    
    # Reinitialize with fresh schema
    init_db()

"""
Game Logic for Sign Language Guessing Game.

Handles game state, scoring, turns, and game flow.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import random

from services.word_bank import get_words_for_selection, check_guess, get_hint


# Points configuration
POINTS_CORRECT_GUESS = 100  # Points for guesser who gets it right
POINTS_ACTOR_BONUS = 50     # Points for actor when someone guesses correctly
POINTS_TIME_BONUS = 10      # Extra points per second remaining
ROUND_TIME_SECONDS = 60     # Time per round


@dataclass
class Player:
    """Represents a player in the game."""
    user_id: str
    username: str
    score: int = 0
    is_ready: bool = False
    has_guessed_correctly: bool = False


@dataclass
class GameRound:
    """Represents a single round of the game."""
    round_number: int
    actor_id: str
    word: str
    category: str
    difficulty: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    guesses: List[Dict[str, Any]] = field(default_factory=list)
    correct_guessers: List[str] = field(default_factory=list)
    hints_used: int = 0


class GameState:
    """
    Manages the state of a sign language guessing game.
    """
    
    def __init__(self, room_code: str):
        self.room_code = room_code
        self.players: Dict[str, Player] = {}
        self.player_order: List[str] = []
        self.current_round: Optional[GameRound] = None
        self.round_history: List[GameRound] = []
        self.total_rounds: int = 0
        self.max_rounds: int = 0  # Will be set based on player count
        self.game_started: bool = False
        self.game_ended: bool = False
        self.current_actor_index: int = 0
        self.difficulty: str = "easy"
        self.created_at: datetime = datetime.now()
    
    def add_player(self, user_id: str, username: str) -> bool:
        """Add a player to the game."""
        if user_id in self.players:
            return False
        
        self.players[user_id] = Player(user_id=user_id, username=username)
        self.player_order.append(user_id)
        return True
    
    def remove_player(self, user_id: str) -> bool:
        """Remove a player from the game."""
        if user_id not in self.players:
            return False
        
        del self.players[user_id]
        self.player_order.remove(user_id)
        
        # Adjust actor index if needed
        if self.current_actor_index >= len(self.player_order):
            self.current_actor_index = 0
        
        return True
    
    def set_player_ready(self, user_id: str, ready: bool = True) -> None:
        """Set a player's ready status."""
        if user_id in self.players:
            self.players[user_id].is_ready = ready
    
    def all_players_ready(self) -> bool:
        """Check if all players are ready."""
        return all(p.is_ready for p in self.players.values()) and len(self.players) >= 2
    
    def can_start_game(self) -> bool:
        """Check if the game can start."""
        return len(self.players) >= 2 and not self.game_started
    
    def start_game(self, rounds_per_player: int = 2) -> bool:
        """Start the game."""
        if not self.can_start_game():
            return False
        
        self.game_started = True
        self.max_rounds = len(self.players) * rounds_per_player
        self.total_rounds = 0
        self.current_actor_index = 0
        
        # Shuffle player order
        random.shuffle(self.player_order)
        
        return True
    
    def get_current_actor(self) -> Optional[str]:
        """Get the current actor's user ID."""
        if not self.player_order:
            return None
        return self.player_order[self.current_actor_index]
    
    def start_new_round(self, word_choice: Dict[str, str]) -> Optional[GameRound]:
        """Start a new round with the selected word."""
        if not self.game_started or self.game_ended:
            return None
        
        actor_id = self.get_current_actor()
        if not actor_id:
            return None
        
        self.total_rounds += 1
        
        # Reset player guess status
        for player in self.players.values():
            player.has_guessed_correctly = False
        
        self.current_round = GameRound(
            round_number=self.total_rounds,
            actor_id=actor_id,
            word=word_choice["word"],
            category=word_choice["category"],
            difficulty=word_choice.get("difficulty", self.difficulty),
            start_time=datetime.now()
        )
        
        return self.current_round
    
    def submit_guess(self, user_id: str, guess: str) -> Dict[str, Any]:
        """
        Submit a guess from a player.
        
        Returns dict with 'correct', 'points', and 'message' keys.
        """
        if not self.current_round:
            return {"correct": False, "points": 0, "message": "No active round"}
        
        if user_id == self.current_round.actor_id:
            return {"correct": False, "points": 0, "message": "Actor cannot guess"}
        
        if user_id not in self.players:
            return {"correct": False, "points": 0, "message": "Player not in game"}
        
        player = self.players[user_id]
        
        if player.has_guessed_correctly:
            return {"correct": False, "points": 0, "message": "Already guessed correctly"}
        
        # Record the guess
        self.current_round.guesses.append({
            "user_id": user_id,
            "username": player.username,
            "guess": guess,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check if correct
        is_correct = check_guess(guess, self.current_round.word)
        
        if is_correct:
            player.has_guessed_correctly = True
            self.current_round.correct_guessers.append(user_id)
            
            # Calculate points
            time_elapsed = (datetime.now() - self.current_round.start_time).seconds
            time_remaining = max(0, ROUND_TIME_SECONDS - time_elapsed)
            
            # More points for earlier guesses
            position_bonus = (len(self.players) - len(self.current_round.correct_guessers)) * 20
            time_bonus = time_remaining * POINTS_TIME_BONUS // 10
            
            total_points = POINTS_CORRECT_GUESS + position_bonus + time_bonus
            player.score += total_points
            
            # Give actor bonus points
            actor = self.players.get(self.current_round.actor_id)
            if actor:
                actor.score += POINTS_ACTOR_BONUS
            
            return {
                "correct": True,
                "points": total_points,
                "message": f"Correct! +{total_points} points"
            }
        
        return {"correct": False, "points": 0, "message": "Wrong guess"}
    
    def end_round(self) -> Dict[str, Any]:
        """End the current round and prepare for next."""
        if not self.current_round:
            return {}
        
        self.current_round.end_time = datetime.now()
        self.round_history.append(self.current_round)
        
        round_summary = {
            "round_number": self.current_round.round_number,
            "word": self.current_round.word,
            "category": self.current_round.category,
            "actor_id": self.current_round.actor_id,
            "correct_guessers": self.current_round.correct_guessers,
            "total_guesses": len(self.current_round.guesses)
        }
        
        # Move to next actor
        self.current_actor_index = (self.current_actor_index + 1) % len(self.player_order)
        
        # Check if game should end
        if self.total_rounds >= self.max_rounds:
            self.game_ended = True
        
        self.current_round = None
        
        return round_summary
    
    def use_hint(self) -> Optional[str]:
        """Use a hint for the current round."""
        if not self.current_round:
            return None
        
        self.current_round.hints_used += 1
        return get_hint(self.current_round.word, self.current_round.hints_used)
    
    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get the current leaderboard."""
        sorted_players = sorted(
            self.players.values(),
            key=lambda p: p.score,
            reverse=True
        )
        
        return [
            {
                "rank": i + 1,
                "user_id": p.user_id,
                "username": p.username,
                "score": p.score
            }
            for i, p in enumerate(sorted_players)
        ]
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get the full game state for synchronization."""
        return {
            "room_code": self.room_code,
            "players": {
                uid: {
                    "username": p.username,
                    "score": p.score,
                    "is_ready": p.is_ready
                }
                for uid, p in self.players.items()
            },
            "game_started": self.game_started,
            "game_ended": self.game_ended,
            "current_round": self.total_rounds,
            "max_rounds": self.max_rounds,
            "current_actor": self.get_current_actor(),
            "difficulty": self.difficulty,
            "leaderboard": self.get_leaderboard()
        }
    
    def get_final_results(self) -> Dict[str, Any]:
        """Get final game results."""
        leaderboard = self.get_leaderboard()
        
        return {
            "winner": leaderboard[0] if leaderboard else None,
            "leaderboard": leaderboard,
            "total_rounds": self.total_rounds,
            "round_history": [
                {
                    "round": r.round_number,
                    "word": r.word,
                    "actor": self.players.get(r.actor_id, {}).username if r.actor_id in self.players else "Unknown",
                    "guessed_by": len(r.correct_guessers)
                }
                for r in self.round_history
            ]
        }


# Global game storage (in production, use Redis or database)
active_games: Dict[str, GameState] = {}


def create_game(room_code: str) -> GameState:
    """Create a new game instance."""
    game = GameState(room_code)
    active_games[room_code] = game
    return game


def get_game(room_code: str) -> Optional[GameState]:
    """Get an existing game by room code."""
    return active_games.get(room_code)


def remove_game(room_code: str) -> bool:
    """Remove a game from storage."""
    if room_code in active_games:
        del active_games[room_code]
        return True
    return False

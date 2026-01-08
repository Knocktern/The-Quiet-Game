"""
Word Bank for Sign Language Guessing Game.

Contains categories of words suitable for sign language guessing.
Words are selected to be easy to demonstrate with hand gestures/signs.
"""

from typing import List, Dict
import random

# Word categories with difficulty levels
WORD_BANK: Dict[str, Dict[str, List[str]]] = {
    "easy": {
        "animals": [
            "cat", "dog", "bird", "fish", "bear", "lion", "tiger", 
            "elephant", "monkey", "rabbit", "duck", "cow", "pig",
            "horse", "snake", "frog", "bee", "butterfly", "spider"
        ],
        "actions": [
            "eat", "drink", "sleep", "run", "walk", "jump", "dance",
            "swim", "fly", "read", "write", "sing", "cry", "laugh",
            "wave", "clap", "point", "push", "pull", "kick"
        ],
        "objects": [
            "ball", "book", "phone", "car", "house", "tree", "flower",
            "sun", "moon", "star", "water", "fire", "door", "window",
            "chair", "table", "bed", "cup", "plate", "key"
        ],
        "food": [
            "apple", "banana", "orange", "pizza", "burger", "cake",
            "ice cream", "bread", "egg", "milk", "coffee", "tea",
            "rice", "fish", "chicken", "cheese", "soup", "salad"
        ]
    },
    "medium": {
        "emotions": [
            "happy", "sad", "angry", "scared", "surprised", "tired",
            "excited", "nervous", "confused", "proud", "shy", "bored"
        ],
        "activities": [
            "cooking", "shopping", "driving", "working", "studying",
            "playing", "painting", "singing", "dancing", "camping",
            "fishing", "hiking", "gardening", "cleaning", "traveling"
        ],
        "nature": [
            "rain", "snow", "wind", "storm", "rainbow", "mountain",
            "river", "ocean", "forest", "desert", "island", "volcano"
        ],
        "sports": [
            "football", "basketball", "tennis", "swimming", "running",
            "boxing", "golf", "baseball", "hockey", "skiing", "surfing"
        ]
    },
    "hard": {
        "concepts": [
            "time", "love", "peace", "freedom", "dream", "hope",
            "future", "past", "memory", "idea", "secret", "promise"
        ],
        "professions": [
            "doctor", "teacher", "police", "firefighter", "chef",
            "artist", "musician", "scientist", "pilot", "farmer"
        ],
        "phrases": [
            "good morning", "thank you", "I love you", "how are you",
            "nice to meet you", "happy birthday", "good night",
            "see you later", "excuse me", "I'm sorry"
        ]
    }
}


def get_random_word(difficulty: str = "easy") -> Dict[str, str]:
    """
    Get a random word from the word bank.
    
    Args:
        difficulty: 'easy', 'medium', or 'hard'
    
    Returns:
        Dictionary with 'word' and 'category' keys
    """
    if difficulty not in WORD_BANK:
        difficulty = "easy"
    
    categories = WORD_BANK[difficulty]
    category = random.choice(list(categories.keys()))
    word = random.choice(categories[category])
    
    return {
        "word": word,
        "category": category,
        "difficulty": difficulty
    }


def get_words_for_selection(difficulty: str = "easy", count: int = 3) -> List[Dict[str, str]]:
    """
    Get multiple word choices for the actor to select from.
    
    Args:
        difficulty: 'easy', 'medium', or 'hard'
        count: Number of words to return
    
    Returns:
        List of word dictionaries
    """
    words = []
    used_words = set()
    
    while len(words) < count:
        word_info = get_random_word(difficulty)
        if word_info["word"] not in used_words:
            used_words.add(word_info["word"])
            words.append(word_info)
    
    return words


def check_guess(guess: str, actual_word: str) -> bool:
    """
    Check if a guess matches the actual word.
    
    Case-insensitive comparison with basic normalization.
    
    Args:
        guess: The player's guess
        actual_word: The word being acted out
    
    Returns:
        True if the guess is correct
    """
    guess_normalized = guess.lower().strip()
    word_normalized = actual_word.lower().strip()
    
    # Exact match
    if guess_normalized == word_normalized:
        return True
    
    # Handle minor variations (e.g., "ice cream" vs "icecream")
    if guess_normalized.replace(" ", "") == word_normalized.replace(" ", ""):
        return True
    
    return False


def get_hint(word: str, hint_level: int = 1) -> str:
    """
    Generate a hint for the word.
    
    Args:
        word: The word to hint at
        hint_level: 1 = first letter, 2 = length, 3 = more letters
    
    Returns:
        A hint string
    """
    if hint_level == 1:
        return f"First letter: {word[0].upper()}"
    elif hint_level == 2:
        return f"Word length: {len(word)} letters"
    elif hint_level >= 3:
        # Show some letters
        revealed = ""
        for i, char in enumerate(word):
            if char == " ":
                revealed += " "
            elif i == 0 or i == len(word) - 1 or random.random() < 0.3:
                revealed += char
            else:
                revealed += "_"
        return f"Word: {revealed}"
    
    return ""


def get_all_categories(difficulty: str = None) -> List[str]:
    """
    Get all available categories.
    
    Args:
        difficulty: Optional filter by difficulty
    
    Returns:
        List of category names
    """
    if difficulty and difficulty in WORD_BANK:
        return list(WORD_BANK[difficulty].keys())
    
    all_categories = set()
    for diff_categories in WORD_BANK.values():
        all_categories.update(diff_categories.keys())
    
    return list(all_categories)

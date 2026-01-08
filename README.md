# 🤫 The Quiet Game

A multiplayer Skribbl-like game where players use **sign language** instead of drawing to act out words for others to guess!

## 🎮 How to Play

1. **Create or Join a Room** - Enter your name and create a new game, or join an existing one with a room code
2. **Wait for Players** - At least 2 players are needed. Mark yourself as "Ready" when prepared
3. **Take Turns Acting** - The actor chooses a word and uses sign language/gestures to help others guess
4. **Guess the Word** - Other players type their guesses in the chat
5. **Score Points** - Correct guesses earn points! Faster guesses = more points

## ✨ Features

- **Real-time Video** - WebRTC-powered video streaming
- **Multiplayer Support** - Play with friends in private rooms
- **Word Categories** - Easy, Medium, and Hard difficulty levels
- **Live Leaderboard** - Track scores in real-time
- **Hints System** - Request hints if stuck
- **Responsive Design** - Play on any device

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Pip

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv env
   ```
3. Activate the environment:
   - Windows: `.\env\Scripts\activate`
   - Mac/Linux: `source env/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the app:
   ```bash
   python app.py
   ```
6. Open http://localhost:5000 in your browser

## 🎯 Game Modes

### Word Difficulty
- **Easy**: Animals, actions, simple objects, food
- **Medium**: Emotions, activities, nature, sports
- **Hard**: Abstract concepts, professions, phrases

### Scoring
- **Correct Guess**: 100+ points (bonus for speed)
- **Actor Bonus**: 50 points when someone guesses correctly
- **Time Bonus**: Extra points for faster guesses

## 🛠 Tech Stack

- **Backend**: Flask + Flask-SocketIO
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Video**: WebRTC
- **Real-time**: Socket.IO

## 📁 Project Structure

```
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── models/             # Database models
├── routes/             # Flask blueprints
│   ├── game.py         # Game routes
│   └── videocall.py    # Video call routes
├── services/           # Business logic
│   ├── game_logic.py   # Game state management
│   └── word_bank.py    # Word categories
├── static/             # Static assets
│   ├── css/
│   └── js/
└── templates/          # HTML templates
```

## 🤝 Contributing

Feel free to open issues and pull requests!

## 📄 License

MIT License

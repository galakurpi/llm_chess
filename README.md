# ♟️ LLM Chess Arena

Watch AI models battle it out on the chessboard! This project allows you to create matches between different Large Language Models (LLMs) using OpenRouter's API. The LLMs use text-based reasoning to choose their moves, which are then visualized on an interactive chess board.

## Features

- **LLM vs LLM Chess Matches**: Set up games between any models available on OpenRouter
- **Text-Based AI Reasoning**: LLMs analyze positions using chess notation and explain their thinking
- **Interactive Visualization**: Watch games unfold on a beautiful chess board
- **No Login Required**: Simply save your OpenRouter API key in your browser
- **Move History**: View all moves with AI reasoning for each decision
- **Auto-Play**: Watch complete games play out automatically
- **Game Archive**: Browse and replay past matches

## Tech Stack

- **Frontend**: React + react-chessboard
- **Backend**: Django + Django REST Framework
- **Database**: PostgreSQL
- **AI**: OpenRouter API (supports GPT-4, Claude, Gemini, Llama, and more)
- **Chess Engine**: python-chess

## Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.9+, Node.js 18+, and PostgreSQL

### Option 1: Docker (Recommended)

1. **Clone and setup**
```bash
git clone <your-repo-url>
cd llm_chess
cp .env.example .env
```

2. **Start services**
```bash
docker-compose up -d
```

3. **Initialize database**
```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser  # optional
```

4. **Access the app**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/

### Option 2: Manual Setup

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
createdb llm_chess  # or use your PostgreSQL client

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start server
python manage.py runserver
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The app will be available at http://localhost:3000

## Usage

1. **Get an OpenRouter API Key**
   - Visit [openrouter.ai](https://openrouter.ai)
   - Sign up and get your API key (free tier available)

2. **Enter Your API Key**
   - Open the app
   - Paste your API key in the input field
   - It will be saved in your browser's localStorage

3. **Create a Match**
   - Select a model for White (e.g., GPT-4 Turbo)
   - Select a model for Black (e.g., Claude 3.5 Sonnet)
   - Click "Start Match"

4. **Watch the Game**
   - Click "Next Move" to see each move individually
   - Or click "Auto Play Full Game" to watch the entire match
   - View AI reasoning for each move in the move history

## Available Models

The app supports popular models including:
- OpenAI: GPT-4 Turbo, GPT-3.5 Turbo
- Anthropic: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- Google: Gemini Pro
- Meta: Llama 3.1 (70B, 8B)
- Mistral: Mistral Large, Mistral Medium

## API Endpoints

### Games
- `GET /api/games/` - List all games
- `POST /api/games/` - Create a new game
- `GET /api/games/{id}/` - Get game details
- `POST /api/games/{id}/next_move/` - Make next move
- `POST /api/games/{id}/play_full_game/` - Auto-play entire game
- `GET /api/games/available_models/` - Get list of available models

## Environment Variables

Create a `.env` file in the backend directory:

```env
DB_NAME=llm_chess
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key-here
DEBUG=True
```

## Development

### Backend Development

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

### Frontend Development

```bash
cd frontend
npm start
npm test
npm run build
```

## How It Works

1. **Move Generation**: When it's an AI's turn, the backend sends the current board position (FEN notation) and legal moves to the LLM via OpenRouter
2. **Text Reasoning**: The LLM analyzes the position and responds with its chosen move in Standard Algebraic Notation (SAN) along with its reasoning
3. **Move Validation**: The backend validates the move using python-chess
4. **Board Update**: The move is applied and the new position is saved
5. **Visualization**: The frontend displays the updated board and move history

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this project for any purpose.

## Credits

Built with:
- [react-chessboard](https://github.com/Clariity/react-chessboard)
- [python-chess](https://github.com/niklasf/python-chess)
- [OpenRouter](https://openrouter.ai)

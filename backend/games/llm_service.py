import requests
import chess
import re
import json


class OpenRouterService:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key):
        self.api_key = api_key

    def get_chess_move(self, board: chess.Board, model: str) -> dict:
        """
        Get a chess move from an LLM using text-based reasoning.
        Returns dict with 'move' (UCI format) and 'thinking' (explanation)
        """
        # Get legal moves in SAN notation
        legal_moves = [board.san(move) for move in board.legal_moves]

        # Create prompt for the LLM
        prompt = self._create_chess_prompt(board, legal_moves)

        # Call OpenRouter API
        response = self._call_openrouter(prompt, model)

        # Parse the response to extract the move
        move_uci, thinking = self._parse_chess_response(response, board)

        return {
            'move': move_uci,
            'thinking': thinking
        }

    def _create_chess_prompt(self, board: chess.Board, legal_moves: list) -> str:
        """Create a prompt for the LLM to choose a chess move."""
        fen = board.fen()
        turn = "White" if board.turn == chess.WHITE else "Black"

        # Get recent moves for context
        move_history = []
        temp_board = chess.Board()
        try:
            for move in board.move_stack[-10:]:  # Last 10 moves
                move_history.append(temp_board.san(move))
                temp_board.push(move)
        except:
            pass

        history_text = " ".join(move_history) if move_history else "Game start"

        prompt = f"""You are playing chess. It is {turn}'s turn to move.

Current position (FEN): {fen}

Recent moves: {history_text}

Legal moves available: {', '.join(legal_moves[:50])}

Please analyze the position and choose your move. Respond in the following format:
THINKING: [Your analysis of the position and why you chose this move]
MOVE: [Your chosen move in standard algebraic notation (SAN), e.g., e4, Nf3, O-O, etc.]

Choose the best move and explain your reasoning."""

        return prompt

    def _call_openrouter(self, prompt: str, model: str) -> str:
        """Call the OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "LLM Chess"
        }

        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }

        response = requests.post(self.BASE_URL, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result['choices'][0]['message']['content']

    def _parse_chess_response(self, response: str, board: chess.Board) -> tuple:
        """
        Parse the LLM response to extract the move and thinking.
        Returns (move_uci, thinking)
        """
        thinking = ""
        move_san = None

        # Try to extract THINKING and MOVE sections
        thinking_match = re.search(r'THINKING:\s*(.+?)(?=MOVE:|$)', response, re.DOTALL | re.IGNORECASE)
        if thinking_match:
            thinking = thinking_match.group(1).strip()

        move_match = re.search(r'MOVE:\s*([^\s\n]+)', response, re.IGNORECASE)
        if move_match:
            move_san = move_match.group(1).strip()

        # If structured format not found, try to find any valid move in the response
        if not move_san:
            words = response.split()
            for word in words:
                # Clean the word
                cleaned = re.sub(r'[^\w\-+=]', '', word)
                try:
                    # Try to parse as SAN
                    move = board.parse_san(cleaned)
                    move_san = cleaned
                    break
                except:
                    continue

        # If we found a SAN move, convert to UCI
        if move_san:
            try:
                move = board.parse_san(move_san)
                return move.uci(), thinking or response
            except:
                pass

        # If all else fails, pick a random legal move
        if list(board.legal_moves):
            random_move = list(board.legal_moves)[0]
            thinking = f"(Failed to parse move from response, using first legal move)\n\nOriginal response: {response}"
            return random_move.uci(), thinking

        raise ValueError("No legal moves available and couldn't parse response")

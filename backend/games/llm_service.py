import requests
import chess
import re
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class OpenRouterService:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    # Models that support reasoning.effort parameter (OpenAI o-series, GPT-5 series, and Grok)
    # Note: Claude uses max_tokens for thinking budget, Gemini uses thinking_budget - different params
    EFFORT_SUPPORTED_MODELS = [
        "openai/o1", "openai/o3", "openai/o4", "openai/o3-mini", "openai/o4-mini",
        "openai/gpt-5", "openai/gpt-5.1", "openai/gpt-5.2",
        "x-ai/grok-3", "x-ai/grok-4",
    ]

    def __init__(self, api_key):
        self.api_key = api_key
    
    def _supports_effort(self, model: str) -> bool:
        """Check if model supports reasoning.effort parameter."""
        return any(model.startswith(prefix) for prefix in self.EFFORT_SUPPORTED_MODELS)

    def get_chess_move(self, board: chess.Board, model: str, reasoning_effort: str = "medium") -> dict:
        """
        Get a chess move from an LLM using text-based reasoning.
        Returns dict with:
        - 'move' (UCI format)
        - 'thinking' (model's REASON: explanation)
        - 'reasoning' (internal reasoning tokens from reasoning models)
        
        reasoning_effort: "none", "minimal", "low", "medium", "high", "xhigh"
        """
        # Get legal moves in SAN notation
        legal_moves = [board.san(move) for move in board.legal_moves]

        # Create prompt for the LLM
        prompt = self._create_chess_prompt(board, legal_moves)

        # Call OpenRouter API
        content, reasoning = self._call_openrouter(prompt, model, reasoning_effort)
        
        logger.debug(f"=== LLM Response from {model} ===")
        logger.debug(f"Content: {content[:500] if content else 'empty'}...")
        logger.debug(f"Reasoning: {reasoning[:500] if reasoning else 'empty'}...")

        # Parse the response to extract the move
        response_to_parse = content or reasoning
        move_uci, thinking = self._parse_chess_response(response_to_parse, board)
        
        logger.debug(f"Parsed move (UCI): {move_uci}")

        return {
            'move': move_uci,
            'thinking': thinking,
            'reasoning': reasoning or ''
        }

    def _create_chess_prompt(self, board: chess.Board, legal_moves: list) -> str:
        """Create a prompt for the LLM to choose a chess move."""
        fen = board.fen()
        turn = "White" if board.turn == chess.WHITE else "Black"

        # Get recent moves for context
        move_history = []
        # Reconstruct the game history from the start of the current board's history
        temp_board = board.copy()
        while temp_board.move_stack:
            temp_board.pop()
        
        for move in board.move_stack:
            move_history.append(temp_board.san(move))
            temp_board.push(move)
            
        # Take last 20 moves for context
        history_text = " ".join(move_history[-20:]) if move_history else "Game start"

        prompt = f"""You are a chess grandmaster. It is {turn}'s turn.

Position (FEN): {fen}
Recent moves: {history_text}
Legal moves (all possible moves, up to 150): {', '.join(legal_moves)}

IMPORTANT: You MUST respond with EXACTLY this format:
MOVE: <your move>
REASON: <brief explanation>

Example response:
MOVE: Nf3
REASON: Develops knight toward center, controls e5 and d4.

Your move must be one of the legal moves listed above. Respond now:"""

        return prompt

    def _call_openrouter(self, prompt: str, model: str, reasoning_effort: str = "medium") -> tuple:
        """
        Call the OpenRouter API.
        Returns tuple of (content, reasoning) where:
        - content: The model's response (MOVE: and REASON:)
        - reasoning: Internal reasoning tokens from reasoning models (may be empty)
        """
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
                    "role": "system",
                    "content": "You are a chess engine. You MUST respond with exactly: MOVE: <move> on the first line, then REASON: <explanation>. Nothing else. The move must be in standard algebraic notation (e.g., e4, Nf3, O-O, Bxc6)."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.05,
        }
        
        # Add reasoning config if model supports it
        if reasoning_effort and reasoning_effort != "none":
            if self._supports_effort(model):
                data["reasoning"] = {"effort": reasoning_effort}
                logger.debug(f"Using reasoning.effort={reasoning_effort} for {model}")
            else:
                logger.debug(f"Model {model} doesn't support reasoning parameters, skipping")
        
        logger.debug(f"Calling OpenRouter with model={model}, reasoning_effort={reasoning_effort}")

        response = requests.post(self.BASE_URL, headers=headers, json=data, timeout=120)
        response.raise_for_status()

        result = response.json()
        logger.debug(f"Raw API response: {json.dumps(result, indent=2)[:1500]}")
        
        content = result['choices'][0]['message'].get('content', '') or ''
        reasoning = result['choices'][0]['message'].get('reasoning', '') or ''
        
        # Handle empty content - retry once
        if not content.strip():
            logger.warning(f"Empty content from {model}, retrying...")
            response = requests.post(self.BASE_URL, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message'].get('content', '') or ''
            reasoning = result['choices'][0]['message'].get('reasoning', '') or ''
        
        return content, reasoning

    def _parse_chess_response(self, response: str, board: chess.Board) -> tuple:
        """
        Parse the LLM response to extract the move and thinking.
        Returns (move_uci, thinking)
        """
        thinking = ""
        move_san = None
        
        # Log full response for debugging
        logger.debug(f"Full response to parse: {response}")

        # Try multiple patterns to extract MOVE
        patterns = [
            r'MOVE:\s*\**([A-Za-z0-9\-+=]+)',  # MOVE: e4 or MOVE: **e4**
            r'\*\*([A-Za-z0-9\-+=]+)\*\*',      # **e4** (bold)
            r'^([A-Za-z0-9\-+=]+)\s*$',          # Just the move on first line
            r'play\s+([A-Za-z0-9\-+=]+)',        # "play e4"
            r'move\s+is\s+([A-Za-z0-9\-+=]+)',   # "move is e4"
            r'choose\s+([A-Za-z0-9\-+=]+)',      # "choose e4"
        ]
        
        for pattern in patterns:
            move_match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if move_match:
                candidate = move_match.group(1).strip()
                # Verify it's a legal move
                try:
                    board.parse_san(candidate)
                    move_san = candidate
                    logger.debug(f"Found move via pattern '{pattern}': {move_san}")
                    break
                except:
                    continue

        # Extract reasoning
        reason_match = re.search(r'(?:REASON|THINKING|EXPLANATION):\s*(.+?)(?=MOVE:|$)', response, re.DOTALL | re.IGNORECASE)
        if reason_match:
            thinking = reason_match.group(1).strip()
        else:
            # Use everything after the move as thinking
            thinking = re.sub(r'^MOVE:\s*[A-Za-z0-9\-+=]+\s*', '', response, flags=re.IGNORECASE).strip()

        # If structured format not found, try to find any valid move in the response
        if not move_san:
            logger.debug("No pattern matched, scanning for any valid move...")
            # Try each word/token
            tokens = re.findall(r'[A-Za-z0-9\-+=]+', response)
            for token in tokens:
                try:
                    board.parse_san(token)
                    move_san = token
                    logger.debug(f"Found move by scanning: {move_san}")
                    break
                except:
                    continue

        # If we found a SAN move, convert to UCI
        if move_san:
            try:
                move = board.parse_san(move_san)
                return move.uci(), thinking or response[:200]
            except Exception as e:
                logger.debug(f"Failed to parse move {move_san}: {e}")

        # If all else fails, pick first legal move
        if list(board.legal_moves):
            random_move = list(board.legal_moves)[0]
            thinking = f"(Failed to parse move from response, using first legal move)\n\nOriginal response: {response[:300]}"
            logger.warning(f"Falling back to first legal move: {random_move}")
            return random_move.uci(), thinking

        raise ValueError("No legal moves available and couldn't parse response")

    def get_chess_move_streaming(self, board: chess.Board, model: str, reasoning_effort: str = "medium"):
        """
        Get a chess move from an LLM with streaming response.
        Yields chunks of reasoning/content as they arrive, then yields final result.
        
        Yields dicts with:
        - {"type": "reasoning", "content": "..."} for internal reasoning token chunks
        - {"type": "content", "content": "..."} for content chunks  
        - {"type": "done", "move": "...", "thinking": "...", "reasoning": "..."} when complete
        - {"type": "error", "error": "..."} on error
        """
        legal_moves = [board.san(move) for move in board.legal_moves]
        prompt = self._create_chess_prompt(board, legal_moves)
        
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
                    "role": "system",
                    "content": "You are a chess engine. You MUST respond with exactly: MOVE: <move> on the first line, then REASON: <explanation>. Nothing else. The move must be in standard algebraic notation (e.g., e4, Nf3, O-O, Bxc6)."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.05,
            "stream": True,
        }
        
        if reasoning_effort and reasoning_effort != "none":
            if self._supports_effort(model):
                data["reasoning"] = {"effort": reasoning_effort}

        try:
            response = requests.post(self.BASE_URL, headers=headers, json=data, stream=True, timeout=120)
            response.raise_for_status()
            
            full_content = ""
            full_reasoning = ""
            
            for line in response.iter_lines():
                if not line:
                    continue
                    
                line = line.decode('utf-8')
                if not line.startswith('data: '):
                    continue
                    
                data_str = line[6:]  # Remove 'data: ' prefix
                if data_str == '[DONE]':
                    break
                    
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get('choices', [{}])[0].get('delta', {})
                    
                    # Handle reasoning_details (OpenRouter's streaming format for reasoning)
                    if 'reasoning_details' in delta and delta['reasoning_details']:
                        for detail in delta['reasoning_details']:
                            if detail.get('type') == 'reasoning.text' and detail.get('text'):
                                reasoning_chunk = detail['text']
                                full_reasoning += reasoning_chunk
                                yield {"type": "reasoning", "content": reasoning_chunk}
                            elif detail.get('type') == 'reasoning.summary' and detail.get('summary'):
                                reasoning_chunk = detail['summary']
                                full_reasoning += reasoning_chunk
                                yield {"type": "reasoning", "content": reasoning_chunk}
                    
                    # Handle simple reasoning field (some models)
                    if 'reasoning' in delta and delta['reasoning']:
                        reasoning_chunk = delta['reasoning']
                        full_reasoning += reasoning_chunk
                        yield {"type": "reasoning", "content": reasoning_chunk}
                    
                    # Handle content chunks (model output)
                    if 'content' in delta and delta['content']:
                        content_chunk = delta['content']
                        full_content += content_chunk
                        yield {"type": "content", "content": content_chunk}
                        
                except json.JSONDecodeError:
                    continue
            
            # Parse final response
            response_to_parse = full_content or full_reasoning
            if response_to_parse:
                move_uci, thinking = self._parse_chess_response(response_to_parse, board)
                yield {
                    "type": "done", 
                    "move": move_uci, 
                    "thinking": thinking,  # Model's REASON: output
                    "reasoning": full_reasoning  # Internal reasoning tokens
                }
            else:
                yield {"type": "error", "error": "Empty response from model"}
                
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {"type": "error", "error": str(e)}

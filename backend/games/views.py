from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from .models import Game, Move
from .serializers import GameSerializer, CreateGameSerializer, MoveSerializer
from .llm_service import OpenRouterService
import chess
import json
from django.contrib.auth.models import User
from django.db import IntegrityError

# Create superuser if it doesn't exist
try:
    if not User.objects.filter(username='jon@yekar.es').exists():
        User.objects.create_superuser('jon@yekar.es', 'jon@yekar.es', 'Ronkolay_824')
        print("Superuser created successfully!")
except Exception as e:
    print(f"Error creating superuser: {e}")


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    def create(self, request):
        """Create a new game between two LLMs."""
        serializer = CreateGameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        game = Game.objects.create(
            white_model=serializer.validated_data['white_model'],
            black_model=serializer.validated_data['black_model'],
            white_reasoning_effort=serializer.validated_data.get('white_reasoning_effort', 'medium'),
            black_reasoning_effort=serializer.validated_data.get('black_reasoning_effort', 'medium')
        )

        return Response(
            GameSerializer(game).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def next_move(self, request, pk=None):
        """
        Make the next move in the game using the appropriate LLM.
        Requires 'api_key' in request data.
        """
        game = self.get_object()

        if game.status != 'active':
            return Response(
                {'error': 'Game is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        api_key = request.data.get('api_key')
        if not api_key:
            return Response(
                {'error': 'API key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Initialize chess board from game state
        board = chess.Board(game.fen)

        # Determine which model and reasoning effort to use
        current_player = 'white' if board.turn == chess.WHITE else 'black'
        model = game.white_model if current_player == 'white' else game.black_model
        reasoning_effort = game.white_reasoning_effort if current_player == 'white' else game.black_reasoning_effort

        try:
            # Get move from LLM
            llm_service = OpenRouterService(api_key)
            result = llm_service.get_chess_move(board, model, reasoning_effort)

            # Apply move to board
            move = chess.Move.from_uci(result['move'])
            san_move = board.san(move)
            board.push(move)

            # Save move to database
            move_number = len(game.moves.all()) + 1
            Move.objects.create(
                game=game,
                move_number=move_number,
                uci_move=result['move'],
                san_move=san_move,
                fen_after=board.fen(),
                player=current_player,
                model_used=model,
                reasoning=result.get('reasoning', ''),
                thinking=result['thinking']
            )

            # Update game state
            game.fen = board.fen()

            # Build PGN
            pgn_moves = []
            for i, m in enumerate(game.moves.all().order_by('move_number')):
                if i % 2 == 0:
                    pgn_moves.append(f"{i//2 + 1}. {m.san_move}")
                else:
                    pgn_moves[-1] += f" {m.san_move}"
            game.pgn = " ".join(pgn_moves)

            # Check if game is over
            if board.is_game_over():
                game.status = 'completed'
                if board.is_checkmate():
                    winner = 'Black' if board.turn == chess.WHITE else 'White'
                    game.result = f'{winner} wins by checkmate'
                elif board.is_stalemate():
                    game.result = 'Draw by stalemate'
                elif board.is_insufficient_material():
                    game.result = 'Draw by insufficient material'
                elif board.is_fifty_moves():
                    game.result = 'Draw by fifty-move rule'
                elif board.is_repetition():
                    game.result = 'Draw by repetition'
                else:
                    game.result = 'Draw'

            game.save()

            return Response(GameSerializer(game).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def next_move_stream(self, request, pk=None):
        """
        Make the next move with streaming response.
        Streams reasoning/content chunks as Server-Sent Events.
        """
        game = self.get_object()

        if game.status != 'active':
            return Response(
                {'error': 'Game is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        api_key = request.data.get('api_key')
        if not api_key:
            return Response(
                {'error': 'API key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        board = chess.Board(game.fen)
        current_player = 'white' if board.turn == chess.WHITE else 'black'
        model = game.white_model if current_player == 'white' else game.black_model
        reasoning_effort = game.white_reasoning_effort if current_player == 'white' else game.black_reasoning_effort

        def event_stream():
            llm_service = OpenRouterService(api_key)
            final_result = None
            
            try:
                for chunk in llm_service.get_chess_move_streaming(board, model, reasoning_effort):
                    if chunk['type'] == 'done':
                        final_result = chunk
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                # After streaming is done, save the move if successful
                if final_result and 'move' in final_result:
                    move_obj = chess.Move.from_uci(final_result['move'])
                    san_move = board.san(move_obj)
                    board.push(move_obj)
                    
                    move_number = len(game.moves.all()) + 1
                    Move.objects.create(
                        game=game,
                        move_number=move_number,
                        uci_move=final_result['move'],
                        san_move=san_move,
                        fen_after=board.fen(),
                        player=current_player,
                        model_used=model,
                        reasoning=final_result.get('reasoning', ''),
                        thinking=final_result.get('thinking', '')
                    )
                    
                    game.fen = board.fen()
                    
                    # Build PGN
                    pgn_moves = []
                    for i, m in enumerate(game.moves.all().order_by('move_number')):
                        if i % 2 == 0:
                            pgn_moves.append(f"{i//2 + 1}. {m.san_move}")
                        else:
                            pgn_moves[-1] += f" {m.san_move}"
                    game.pgn = " ".join(pgn_moves)
                    
                    # Check if game is over
                    if board.is_game_over():
                        game.status = 'completed'
                        if board.is_checkmate():
                            winner = 'Black' if board.turn == chess.WHITE else 'White'
                            game.result = f'{winner} wins by checkmate'
                        elif board.is_stalemate():
                            game.result = 'Draw by stalemate'
                        elif board.is_insufficient_material():
                            game.result = 'Draw by insufficient material'
                        elif board.is_fifty_moves():
                            game.result = 'Draw by fifty-move rule'
                        elif board.is_repetition():
                            game.result = 'Draw by repetition'
                        else:
                            game.result = 'Draw'
                    
                    game.save()
                    
                    # Send final game state
                    yield f"data: {json.dumps({'type': 'game_update', 'game': GameSerializer(game).data})}\n\n"
                    
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    @action(detail=True, methods=['post'])
    def play_full_game(self, request, pk=None):
        """
        Play a complete game automatically.
        Requires 'api_key' in request data.
        Optional 'max_moves' parameter (default 100).
        """
        game = self.get_object()

        if game.status != 'active':
            return Response(
                {'error': 'Game is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        api_key = request.data.get('api_key')
        if not api_key:
            return Response(
                {'error': 'API key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        max_moves = request.data.get('max_moves', 100)

        try:
            llm_service = OpenRouterService(api_key)
            board = chess.Board(game.fen)

            move_count = 0
            while not board.is_game_over() and move_count < max_moves:
                # Determine current player, model, and reasoning effort
                current_player = 'white' if board.turn == chess.WHITE else 'black'
                model = game.white_model if current_player == 'white' else game.black_model
                reasoning_effort = game.white_reasoning_effort if current_player == 'white' else game.black_reasoning_effort

                # Get and apply move
                result = llm_service.get_chess_move(board, model, reasoning_effort)
                move = chess.Move.from_uci(result['move'])
                san_move = board.san(move)
                board.push(move)

                # Save move
                move_number = len(game.moves.all()) + 1
                Move.objects.create(
                    game=game,
                    move_number=move_number,
                    uci_move=result['move'],
                    san_move=san_move,
                    fen_after=board.fen(),
                    player=current_player,
                    model_used=model,
                    reasoning=result.get('reasoning', ''),
                    thinking=result['thinking']
                )

                move_count += 1

            # Update final game state
            game.fen = board.fen()

            # Build PGN
            pgn_moves = []
            for i, m in enumerate(game.moves.all().order_by('move_number')):
                if i % 2 == 0:
                    pgn_moves.append(f"{i//2 + 1}. {m.san_move}")
                else:
                    pgn_moves[-1] += f" {m.san_move}"
            game.pgn = " ".join(pgn_moves)

            # Set game result
            if board.is_game_over():
                game.status = 'completed'
                if board.is_checkmate():
                    winner = 'Black' if board.turn == chess.WHITE else 'White'
                    game.result = f'{winner} wins by checkmate'
                elif board.is_stalemate():
                    game.result = 'Draw by stalemate'
                elif board.is_insufficient_material():
                    game.result = 'Draw by insufficient material'
                elif board.is_fifty_moves():
                    game.result = 'Draw by fifty-move rule'
                elif board.is_repetition():
                    game.result = 'Draw by repetition'
                else:
                    game.result = 'Draw'
            else:
                game.status = 'completed'
                game.result = f'Game stopped after {max_moves} moves'

            game.save()

            return Response(GameSerializer(game).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def available_models(self, request):
        """Return a list of popular models available on OpenRouter."""
        # Models that support reasoning.effort parameter
        effort_supported = {
            "openai/o1", "openai/o3", "openai/o4", "openai/o3-mini", "openai/o4-mini",
            "openai/gpt-5", "openai/gpt-5.1", "openai/gpt-5.2",
            "x-ai/grok-3", "x-ai/grok-4",
        }
        
        models = [
            # Top Tier (Flagship - Best Performance)
            {"id": "openai/gpt-5.2", "name": "GPT-5.2 (Latest)"},
            {"id": "anthropic/claude-opus-4.5", "name": "Claude Opus 4.5"},
            {"id": "anthropic/claude-sonnet-4.5", "name": "Claude Sonnet 4.5"},
            {"id": "google/gemini-3-pro-preview", "name": "Gemini 3 Pro"},
            {"id": "x-ai/grok-4", "name": "Grok 4"},
            {"id": "openai/gpt-5.1", "name": "GPT-5.1"},
            {"id": "openai/gpt-5", "name": "GPT-5"},
            
            # Strong Performers
            {"id": "moonshotai/kimi-k2", "name": "Kimi K2"},
            {"id": "anthropic/claude-haiku-4.5", "name": "Claude Haiku 4.5"},
            {"id": "anthropic/claude-opus-4.1", "name": "Claude Opus 4.1"},
            {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4"},
            {"id": "google/gemini-3-flash-preview", "name": "Gemini 3 Flash"},
            {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "openai/o3", "name": "OpenAI o3"},
            {"id": "openai/o4-mini", "name": "OpenAI o4-mini"},
            
            # Great Value
            {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
            {"id": "anthropic/claude-3.7-sonnet", "name": "Claude 3.7 Sonnet"},
            {"id": "x-ai/grok-3", "name": "Grok 3"},
            {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1"},
            {"id": "openai/o3-mini", "name": "OpenAI o3-mini"},
            {"id": "meta-llama/llama-4-maverick", "name": "Llama 4 Maverick"},
        ]
        
        # Add supports_effort flag to each model
        for model in models:
            model["supports_effort"] = model["id"] in effort_supported
        
        return Response(models)

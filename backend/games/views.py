from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Game, Move
from .serializers import GameSerializer, CreateGameSerializer, MoveSerializer
from .llm_service import OpenRouterService
import chess


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    def create(self, request):
        """Create a new game between two LLMs."""
        serializer = CreateGameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        game = Game.objects.create(
            white_model=serializer.validated_data['white_model'],
            black_model=serializer.validated_data['black_model']
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

        # Determine which model to use
        current_player = 'white' if board.turn == chess.WHITE else 'black'
        model = game.white_model if current_player == 'white' else game.black_model

        try:
            # Get move from LLM
            llm_service = OpenRouterService(api_key)
            result = llm_service.get_chess_move(board, model)

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
                # Determine current player and model
                current_player = 'white' if board.turn == chess.WHITE else 'black'
                model = game.white_model if current_player == 'white' else game.black_model

                # Get and apply move
                result = llm_service.get_chess_move(board, model)
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
        models = [
            {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "openai/gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
            {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus"},
            {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku"},
            {"id": "google/gemini-pro", "name": "Gemini Pro"},
            {"id": "meta-llama/llama-3.1-70b-instruct", "name": "Llama 3.1 70B"},
            {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B"},
            {"id": "mistralai/mistral-large", "name": "Mistral Large"},
            {"id": "mistralai/mistral-medium", "name": "Mistral Medium"},
        ]
        return Response(models)

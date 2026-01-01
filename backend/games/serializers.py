from rest_framework import serializers
from .models import Game, Move


class MoveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Move
        fields = ['id', 'move_number', 'uci_move', 'san_move', 'fen_after',
                  'player', 'model_used', 'thinking', 'created_at']


class GameSerializer(serializers.ModelSerializer):
    moves = MoveSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = ['id', 'white_model', 'black_model', 'fen', 'pgn', 'status',
                  'result', 'created_at', 'updated_at', 'moves']
        read_only_fields = ['fen', 'pgn', 'status', 'result', 'created_at', 'updated_at']


class CreateGameSerializer(serializers.Serializer):
    white_model = serializers.CharField(max_length=200)
    black_model = serializers.CharField(max_length=200)

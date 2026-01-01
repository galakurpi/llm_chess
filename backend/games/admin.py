from django.contrib import admin
from .models import Game, Move


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['id', 'white_model', 'black_model', 'status', 'result', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['white_model', 'black_model']


@admin.register(Move)
class MoveAdmin(admin.ModelAdmin):
    list_display = ['id', 'game', 'move_number', 'san_move', 'player', 'model_used', 'created_at']
    list_filter = ['player', 'created_at']
    search_fields = ['game__id', 'san_move']

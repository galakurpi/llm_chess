from django.db import models
import chess
import json


class Game(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]

    EFFORT_CHOICES = [
        ('none', 'None'),
        ('minimal', 'Minimal'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('xhigh', 'Extra High'),
    ]

    white_model = models.CharField(max_length=200)
    black_model = models.CharField(max_length=200)
    white_reasoning_effort = models.CharField(max_length=20, choices=EFFORT_CHOICES, default='medium')
    black_reasoning_effort = models.CharField(max_length=20, choices=EFFORT_CHOICES, default='medium')
    fen = models.TextField(default=chess.STARTING_FEN)
    pgn = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    result = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Game {self.id}: {self.white_model} vs {self.black_model}"

    class Meta:
        ordering = ['-created_at']


class Move(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='moves')
    move_number = models.IntegerField()
    uci_move = models.CharField(max_length=10)
    san_move = models.CharField(max_length=20)
    fen_after = models.TextField()
    player = models.CharField(max_length=10)  # 'white' or 'black'
    model_used = models.CharField(max_length=200)
    reasoning = models.TextField(blank=True, default='')  # Internal reasoning tokens from reasoning models
    thinking = models.TextField(blank=True, default='')   # Model's explanation for the move (REASON: output)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Move {self.move_number} in Game {self.game.id}: {self.san_move}"

    class Meta:
        ordering = ['move_number']

import React, { useState, useEffect } from 'react';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';
import axios from 'axios';
import './GameViewer.css';

function GameViewer({ game, apiKey, onBack, onGameUpdate }) {
  const [currentGame, setCurrentGame] = useState(game);
  const [chess] = useState(new Chess());
  const [loading, setLoading] = useState(false);
  const [autoPlaying, setAutoPlaying] = useState(false);
  const [error, setError] = useState('');
  const [selectedMove, setSelectedMove] = useState(null);

  useEffect(() => {
    if (currentGame) {
      chess.load(currentGame.fen);
      setCurrentGame(currentGame);
    }
  }, [currentGame, chess]);

  const refreshGame = async () => {
    try {
      const response = await axios.get(`/api/games/${currentGame.id}/`);
      setCurrentGame(response.data);
      onGameUpdate(response.data);
      chess.load(response.data.fen);
    } catch (err) {
      console.error('Error refreshing game:', err);
    }
  };

  const makeNextMove = async () => {
    if (currentGame.status !== 'active') {
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`/api/games/${currentGame.id}/next_move/`, {
        api_key: apiKey,
      });

      setCurrentGame(response.data);
      onGameUpdate(response.data);
      chess.load(response.data.fen);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to make move');
    } finally {
      setLoading(false);
    }
  };

  const playFullGame = async () => {
    if (currentGame.status !== 'active') {
      return;
    }

    setAutoPlaying(true);
    setError('');

    try {
      const response = await axios.post(`/api/games/${currentGame.id}/play_full_game/`, {
        api_key: apiKey,
        max_moves: 100,
      });

      setCurrentGame(response.data);
      onGameUpdate(response.data);
      chess.load(response.data.fen);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to play game');
    } finally {
      setAutoPlaying(false);
    }
  };

  const viewMovePosition = (move) => {
    setSelectedMove(move);
    chess.load(move.fen_after);
  };

  const viewCurrentPosition = () => {
    setSelectedMove(null);
    chess.load(currentGame.fen);
  };

  const getTurnIndicator = () => {
    if (currentGame.status !== 'active') {
      return 'Game Over';
    }
    const board = new Chess(currentGame.fen);
    return board.turn === 'w' ? "White's turn" : "Black's turn";
  };

  return (
    <div className="game-viewer">
      <button onClick={onBack} className="btn btn-back">
        ← Back to Setup
      </button>

      <div className="game-content">
        <div className="board-section">
          <div className="board-header">
            <div className="player-info">
              <span className="player-icon">⚫</span>
              <span className="player-name">{currentGame.black_model}</span>
            </div>
          </div>

          <div className="board-container">
            <Chessboard
              position={chess.fen()}
              boardWidth={Math.min(500, window.innerWidth - 40)}
              arePiecesDraggable={false}
            />
          </div>

          <div className="board-header">
            <div className="player-info">
              <span className="player-icon">⚪</span>
              <span className="player-name">{currentGame.white_model}</span>
            </div>
          </div>

          <div className="game-status">
            <div className="status-badge">
              {currentGame.status === 'active' ? (
                <span className="status-active">{getTurnIndicator()}</span>
              ) : (
                <span className="status-completed">{currentGame.result}</span>
              )}
            </div>
          </div>

          {currentGame.status === 'active' && (
            <div className="controls">
              <button
                onClick={makeNextMove}
                disabled={loading || autoPlaying}
                className="btn btn-primary"
              >
                {loading ? 'Thinking...' : 'Next Move'}
              </button>
              <button
                onClick={playFullGame}
                disabled={loading || autoPlaying}
                className="btn btn-secondary"
              >
                {autoPlaying ? 'Playing...' : 'Auto Play Full Game'}
              </button>
              <button
                onClick={refreshGame}
                disabled={loading || autoPlaying}
                className="btn btn-secondary"
              >
                Refresh
              </button>
            </div>
          )}

          {error && <div className="error-message">{error}</div>}
        </div>

        <div className="moves-section">
          <h3>Move History ({currentGame.moves?.length || 0} moves)</h3>
          <div className="moves-list">
            {currentGame.moves && currentGame.moves.length > 0 ? (
              <>
                {currentGame.moves.map((move, index) => (
                  <div
                    key={move.id}
                    className={`move-item ${selectedMove?.id === move.id ? 'selected' : ''}`}
                    onClick={() => viewMovePosition(move)}
                  >
                    <div className="move-header">
                      <span className="move-number">
                        {move.move_number}. {move.san_move}
                      </span>
                      <span className={`move-player ${move.player}`}>
                        {move.player === 'white' ? '⚪' : '⚫'}
                      </span>
                    </div>
                    {move.thinking && (
                      <div className="move-thinking">
                        {move.thinking.length > 150
                          ? move.thinking.substring(0, 150) + '...'
                          : move.thinking}
                      </div>
                    )}
                  </div>
                ))}
                {selectedMove && (
                  <button onClick={viewCurrentPosition} className="btn btn-small btn-secondary">
                    Back to Current Position
                  </button>
                )}
              </>
            ) : (
              <div className="no-moves">No moves yet</div>
            )}
          </div>

          {currentGame.pgn && (
            <div className="pgn-section">
              <h4>PGN</h4>
              <div className="pgn-content">
                <code>{currentGame.pgn}</code>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default GameViewer;

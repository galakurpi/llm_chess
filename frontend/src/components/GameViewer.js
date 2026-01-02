import React, { useState, useEffect } from 'react';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';
import axios from 'axios';
import './GameViewer.css';

// Models that support reasoning effort parameter
const EFFORT_SUPPORTED_PREFIXES = [
  "openai/o1", "openai/o3", "openai/o4", "openai/o3-mini", "openai/o4-mini",
  "openai/gpt-5", "x-ai/grok-3", "x-ai/grok-4",
];

function GameViewer({ game, apiKey, onBack, onGameUpdate }) {
  const [currentGame, setCurrentGame] = useState(game);
  const [chess] = useState(new Chess());
  const [loading, setLoading] = useState(false);
  const [autoPlaying, setAutoPlaying] = useState(false);
  const [error, setError] = useState('');
  const [selectedMove, setSelectedMove] = useState(null);
  const [expandedMoves, setExpandedMoves] = useState({});
  const [streamingReasoning, setStreamingReasoning] = useState('');
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingMoveModel, setPendingMoveModel] = useState('');

  // Check if a model supports reasoning effort
  const modelSupportsEffort = (modelId) => {
    return EFFORT_SUPPORTED_PREFIXES.some(prefix => modelId?.startsWith(prefix));
  };

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

  const makeNextMove = async (useStreaming = true) => {
    if (currentGame.status !== 'active') {
      return;
    }

    setLoading(true);
    setError('');
    setStreamingReasoning('');
    setStreamingContent('');

    // Determine which model is playing
    const board = new Chess(currentGame.fen);
    const currentPlayer = board.turn() === 'w' ? 'white' : 'black';
    const currentModel = currentPlayer === 'white' ? currentGame.white_model : currentGame.black_model;
    setPendingMoveModel(currentModel);

    if (useStreaming) {
      // Use streaming endpoint
      setIsStreaming(true);
      try {
        const response = await fetch(`/api/games/${currentGame.id}/next_move_stream/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ api_key: apiKey }),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'reasoning') {
                  setStreamingReasoning(prev => prev + data.content);
                } else if (data.type === 'content') {
                  setStreamingContent(prev => prev + data.content);
                } else if (data.type === 'game_update') {
                  setCurrentGame(data.game);
                  onGameUpdate(data.game);
                  chess.load(data.game.fen);
                } else if (data.type === 'error') {
                  setError(data.error);
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      } catch (err) {
        setError(err.message || 'Failed to make move');
      } finally {
        setIsStreaming(false);
        setLoading(false);
        setStreamingReasoning('');
        setStreamingContent('');
        setPendingMoveModel('');
      }
    } else {
      // Use regular endpoint
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
    }
  };

  const playFullGame = async () => {
    if (currentGame.status !== 'active') {
      return;
    }

    setAutoPlaying(true);
    setError('');

    try {
      // Play move by move so UI updates in real-time
      let gameData = currentGame;
      while (gameData.status === 'active') {
        const response = await axios.post(`/api/games/${gameData.id}/next_move/`, {
          api_key: apiKey,
        });
        gameData = response.data;
        setCurrentGame(gameData);
        onGameUpdate(gameData);
        chess.load(gameData.fen);
        
        // Small delay to let the UI breathe
        await new Promise(resolve => setTimeout(resolve, 300));
      }
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

  const toggleMoveExpanded = (moveId, e) => {
    e.stopPropagation();
    setExpandedMoves(prev => ({
      ...prev,
      [moveId]: !prev[moveId]
    }));
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
              {modelSupportsEffort(currentGame.black_model) && (
                <span className="player-effort">({currentGame.black_reasoning_effort || 'medium'})</span>
              )}
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
              {modelSupportsEffort(currentGame.white_model) && (
                <span className="player-effort">({currentGame.white_reasoning_effort || 'medium'})</span>
              )}
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
                onClick={() => makeNextMove(true)}
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
                    <div className="move-model">
                      {move.model_used?.split('/').pop() || move.model_used}
                    </div>
                    {/* Model's explanation - always visible */}
                    {move.thinking && (
                      <div className="move-thinking">
                        {move.thinking}
                      </div>
                    )}
                    {/* Internal reasoning tokens - expandable */}
                    {move.reasoning && (
                      <div className="move-reasoning-container">
                        <button 
                          className="expand-btn"
                          onClick={(e) => toggleMoveExpanded(move.id, e)}
                          title={expandedMoves[move.id] ? 'Hide internal reasoning' : 'Show internal reasoning'}
                        >
                          {expandedMoves[move.id] ? '▲' : '▼'} reasoning
                        </button>
                        {expandedMoves[move.id] && (
                          <div className="move-reasoning">
                            {move.reasoning}
                          </div>
                        )}
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
              !isStreaming && <div className="no-moves">No moves yet</div>
            )}
            
            {/* Streaming/pending move */}
            {isStreaming && (
              <div className="move-item pending">
                <div className="move-header">
                  <span className="move-number">
                    <span className="streaming-dot"></span> Thinking...
                  </span>
                  <span className="move-player">
                    {new Chess(currentGame.fen).turn() === 'w' ? '⚪' : '⚫'}
                  </span>
                </div>
                <div className="move-model">
                  {pendingMoveModel?.split('/').pop() || pendingMoveModel}
                </div>
                {/* Streaming content (MOVE/REASON output) */}
                {streamingContent && (
                  <div className="move-thinking streaming">
                    {streamingContent}
                  </div>
                )}
                {/* Streaming internal reasoning */}
                {streamingReasoning && (
                  <div className="move-reasoning-container">
                    <span className="reasoning-label">reasoning</span>
                    <div className="move-reasoning streaming">
                      {streamingReasoning}
                    </div>
                  </div>
                )}
              </div>
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

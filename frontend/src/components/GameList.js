import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './GameList.css';

function GameList({ apiKey, onSelectGame }) {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGames();
  }, []);

  const fetchGames = async () => {
    try {
      const response = await axios.get('/api/games/');
      setGames(response.data);
    } catch (err) {
      console.error('Error fetching games:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  if (loading) {
    return <div className="game-list loading">Loading games...</div>;
  }

  if (games.length === 0) {
    return null;
  }

  return (
    <div className="game-list">
      <h2>📜 Recent Games</h2>
      <div className="games-grid">
        {games.map((game) => (
          <div
            key={game.id}
            className="game-card"
            onClick={() => onSelectGame(game)}
          >
            <div className="game-card-header">
              <span className="game-id">Game #{game.id}</span>
              <span className={`game-status-badge ${game.status}`}>
                {game.status}
              </span>
            </div>

            <div className="game-matchup">
              <div className="matchup-player">
                <span className="player-icon">⚪</span>
                <span className="player-model">{game.white_model.split('/').pop()}</span>
              </div>
              <div className="matchup-vs">VS</div>
              <div className="matchup-player">
                <span className="player-icon">⚫</span>
                <span className="player-model">{game.black_model.split('/').pop()}</span>
              </div>
            </div>

            {game.result && (
              <div className="game-result">{game.result}</div>
            )}

            <div className="game-meta">
              <span className="game-moves">{game.moves?.length || 0} moves</span>
              <span className="game-date">{formatDate(game.created_at)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default GameList;

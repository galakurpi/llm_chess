import React, { useState, useEffect } from 'react';
import './App.css';
import ApiKeyManager from './components/ApiKeyManager';
import GameSetup from './components/GameSetup';
import GameViewer from './components/GameViewer';
import GameList from './components/GameList';

function App() {
  const [apiKey, setApiKey] = useState('');
  const [currentGame, setCurrentGame] = useState(null);
  const [view, setView] = useState('setup'); // 'setup' or 'game'

  useEffect(() => {
    // Load API key from localStorage
    const savedKey = localStorage.getItem('openrouter_api_key');
    if (savedKey) {
      setApiKey(savedKey);
    }
  }, []);

  const handleApiKeyChange = (newKey) => {
    setApiKey(newKey);
    if (newKey) {
      localStorage.setItem('openrouter_api_key', newKey);
    } else {
      localStorage.removeItem('openrouter_api_key');
    }
  };

  const handleGameCreated = (game) => {
    setCurrentGame(game);
    setView('game');
  };

  const handleBackToSetup = () => {
    setCurrentGame(null);
    setView('setup');
  };

  const handleSelectGame = (game) => {
    setCurrentGame(game);
    setView('game');
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>♟️ LLM Chess Arena</h1>
        <p className="subtitle">Watch AI models battle it out on the chessboard</p>
      </header>

      <div className="container">
        <ApiKeyManager apiKey={apiKey} onApiKeyChange={handleApiKeyChange} />

        {!apiKey ? (
          <div className="warning-box">
            <h3>⚠️ API Key Required</h3>
            <p>Please enter your OpenRouter API key above to start playing.</p>
            <p className="small">Get your free key at <a href="https://openrouter.ai" target="_blank" rel="noopener noreferrer">openrouter.ai</a></p>
          </div>
        ) : (
          <>
            {view === 'setup' ? (
              <>
                <GameSetup 
                  apiKey={apiKey} 
                  onGameCreated={handleGameCreated}
                />
                <GameList apiKey={apiKey} onSelectGame={handleSelectGame} />
              </>
            ) : (
              <GameViewer
                game={currentGame}
                apiKey={apiKey}
                onBack={handleBackToSetup}
                onGameUpdate={setCurrentGame}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;

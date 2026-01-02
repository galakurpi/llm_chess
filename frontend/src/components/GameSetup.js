import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './GameSetup.css';

function GameSetup({ apiKey, onGameCreated }) {
  const [models, setModels] = useState([]);
  const [whiteModel, setWhiteModel] = useState('');
  const [blackModel, setBlackModel] = useState('');
  const [whiteReasoningEffort, setWhiteReasoningEffort] = useState('medium');
  const [blackReasoningEffort, setBlackReasoningEffort] = useState('medium');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const reasoningOptions = [
    { value: 'none', label: 'None (fastest)' },
    { value: 'minimal', label: 'Minimal' },
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'xhigh', label: 'Extra High' },
  ];

  // Check if a model supports reasoning effort
  const modelSupportsEffort = (modelId) => {
    const model = models.find(m => m.id === modelId);
    return model?.supports_effort || false;
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await axios.get('/api/games/available_models/');
      setModels(response.data);
      if (response.data.length >= 2) {
        setWhiteModel(response.data[0].id);
        setBlackModel(response.data[1].id);
      }
    } catch (err) {
      console.error('Error fetching models:', err);
    }
  };

  const handleCreateGame = async () => {
    if (!whiteModel || !blackModel) {
      setError('Please select both models');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/games/', {
        white_model: whiteModel,
        black_model: blackModel,
        white_reasoning_effort: whiteReasoningEffort,
        black_reasoning_effort: blackReasoningEffort,
      });

      onGameCreated(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create game');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="game-setup">
      <h2>⚔️ Create New Match</h2>

      <div className="model-selection">
        <div className="model-selector">
          <label>
            <span className="label-icon">⚪</span> White
          </label>
          <select
            value={whiteModel}
            onChange={(e) => setWhiteModel(e.target.value)}
            className="model-select"
          >
            <option value="">Select a model...</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
          {modelSupportsEffort(whiteModel) && (
            <select
              value={whiteReasoningEffort}
              onChange={(e) => setWhiteReasoningEffort(e.target.value)}
              className="effort-select"
            >
              {reasoningOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="vs-divider">VS</div>

        <div className="model-selector">
          <label>
            <span className="label-icon">⚫</span> Black
          </label>
          <select
            value={blackModel}
            onChange={(e) => setBlackModel(e.target.value)}
            className="model-select"
          >
            <option value="">Select a model...</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
          {modelSupportsEffort(blackModel) && (
            <select
              value={blackReasoningEffort}
              onChange={(e) => setBlackReasoningEffort(e.target.value)}
              className="effort-select"
            >
              {reasoningOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {(modelSupportsEffort(whiteModel) || modelSupportsEffort(blackModel)) && (
        <p className="reasoning-hint">
          Reasoning effort: higher = better moves but slower and more expensive.
        </p>
      )}

      {error && <div className="error-message">{error}</div>}

      <button
        onClick={handleCreateGame}
        disabled={loading || !whiteModel || !blackModel}
        className="btn btn-large btn-primary"
      >
        {loading ? 'Creating...' : 'Start Match'}
      </button>
    </div>
  );
}

export default GameSetup;

import React, { useState } from 'react';
import './ApiKeyManager.css';

function ApiKeyManager({ apiKey, onApiKeyChange }) {
  const [isEditing, setIsEditing] = useState(!apiKey);
  const [inputValue, setInputValue] = useState(apiKey);
  const [showKey, setShowKey] = useState(false);

  const handleSave = () => {
    onApiKeyChange(inputValue);
    setIsEditing(false);
  };

  const handleClear = () => {
    setInputValue('');
    onApiKeyChange('');
    setIsEditing(true);
  };

  const maskKey = (key) => {
    if (!key) return '';
    return key.slice(0, 10) + '...' + key.slice(-4);
  };

  return (
    <div className="api-key-manager">
      <h3>🔑 OpenRouter API Key</h3>

      {isEditing ? (
        <div className="edit-mode">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="sk-or-v1-..."
            className="api-key-input"
          />
          <div className="button-group">
            <button onClick={handleSave} className="btn btn-primary">
              Save
            </button>
            {apiKey && (
              <button onClick={() => setIsEditing(false)} className="btn btn-secondary">
                Cancel
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="view-mode">
          <div className="key-display">
            <code>{showKey ? apiKey : maskKey(apiKey)}</code>
            <button
              onClick={() => setShowKey(!showKey)}
              className="btn btn-icon"
              title={showKey ? 'Hide' : 'Show'}
            >
              {showKey ? '🙈' : '👁️'}
            </button>
          </div>
          <div className="button-group">
            <button onClick={() => setIsEditing(true)} className="btn btn-secondary">
              Edit
            </button>
            <button onClick={handleClear} className="btn btn-danger">
              Clear
            </button>
          </div>
        </div>
      )}

      <p className="help-text">
        Your API key is stored locally in your browser. Get a free key at{' '}
        <a href="https://openrouter.ai" target="_blank" rel="noopener noreferrer">
          openrouter.ai
        </a>
      </p>
    </div>
  );
}

export default ApiKeyManager;

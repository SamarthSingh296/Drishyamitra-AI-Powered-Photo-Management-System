import React, { useEffect, useState } from 'react';
import logo from './logo.svg';
import './App.css';

function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_API_URL}/api/health`)
      .then(response => { 
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => setHealth(data))
      .catch(err => {
        console.error('Fetch error:', err);
        setError(err.message);
      });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <h1>Drishyamitra</h1>
        <div style={{ padding: '20px', border: '1px solid white', borderRadius: '10px' }}>
          <h3>Backend Connection Status:</h3>
          {health ? (
            <div style={{ color: '#28a745' }}>
              <p>✅ Connected</p>
              <p>Status: {health.status}</p>
              <p>Version: {health.version}</p>
            </div>
          ) : error ? (
            <div style={{ color: '#dc3545' }}>
              <p>❌ Error: {error}</p>
            </div>
          ) : (
            <p>⌛ Checking connection...</p>
          )}
        </div>
      </header>
    </div>
  );
}

export default App;

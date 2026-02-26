import React, { useState, useEffect, useRef } from 'react';
import './App.css';

let API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';
if (!API_BASE.endsWith('/api')) {
  API_BASE = `${API_BASE}/api`;
}

function App() {
  const [view, setView] = useState('landing'); // landing, auth, dashboard, chat
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [photos, setPhotos] = useState([]);
  const [stats, setStats] = useState({ photo_count: 0, person_count: 0, history_count: 0 });
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState([{ role: 'bot', content: 'Hello! How can I help you manage your photos today?' }]);
  const [chatInput, setChatInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    if (token) {
      fetchPhotos();
      fetchStats();
    }
  }, [token]);

  const fetchPhotos = async () => {
    try {
      const res = await fetch(`${API_BASE}/photos/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.status === 'success') setPhotos(data.data);
    } catch (err) { console.error("Fetch photos failed", err); }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/dashboard/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.status === 'success') setStats(data.data);
    } catch (err) { console.error("Fetch stats failed", err); }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('photo', file);

    try {
      const res = await fetch(`${API_BASE}/photos/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();
      if (data.status === 'success') {
        fetchPhotos();
        fetchStats();
      } else {
        alert(data.message || "Upload failed");
      }
    } catch (err) {
      console.error("Upload error:", err);
      alert("Connection error during upload.");
    } finally {
      setUploading(false);
    }
  };

  const [authMode, setAuthMode] = useState('login'); // login, signup
  const [authError, setAuthError] = useState('');

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setAuthError('');

    const fields = e.target;
    const username = fields[0].value;
    const password = authMode === 'login' ? fields[1].value : fields[2].value;
    const email = authMode === 'signup' ? fields[1].value : '';

    const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
    const payload = authMode === 'login' ? { username, password } : { username, email, password };

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (data.status === 'success') {
        if (authMode === 'login') {
          setUser(data.data.user);
          setToken(data.data.token);
          localStorage.setItem('token', data.data.token);
          setView('dashboard');
        } else {
          alert("Registration successful! Please login.");
          setAuthMode('login');
        }
      } else {
        setAuthError(data.message || `${authMode} failed`);
      }
    } catch (err) {
      console.error(`${authMode} error:`, err);
      setAuthError(`Connection error: ${err.message}. Is the backend running?`);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      const res = await fetch(`${API_BASE}/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: userMessage, history })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setMessages(prev => [...prev, { role: 'bot', content: data.data.response }]);
      }
    } catch (err) {
      console.error("Chat error:", err);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="App">
      <nav className="navbar animate-fade-in">
        <div className="logo">Drishyamitra<span>AI</span></div>
        <div className="nav-links">
          {token ? (
            <button className="btn-primary" onClick={() => { localStorage.removeItem('token'); setToken(null); setView('landing'); }}>Logout</button>
          ) : (
            <button className="btn-primary" onClick={() => setView('auth')}>Login</button>
          )}
        </div>
      </nav>

      <main className="container">
        {view === 'landing' && (
          <section className="hero animate-fade-in">
            <h1 className="hero-title">Intelligent Photo Management <span>Redefined</span></h1>
            <p className="hero-subtitle">Organize, recognize, and interact with your memories using cutting-edge AI.</p>
            <button className="btn-primary btn-large" onClick={() => setView('auth')}>Get Started Free</button>
          </section>
        )}

        {view === 'auth' && (
          <div className="auth-card glass-card animate-fade-in">
            <h2>{authMode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
            {authError && <div className="error-msg">{authError}</div>}
            <form onSubmit={handleAuth}>
              <input type="text" placeholder="Username" required />
              {authMode === 'signup' && <input type="email" placeholder="Email" required />}
              <input type="password" placeholder="Password" required />
              <button className="btn-primary w-full" type="submit" disabled={loading}>
                {loading ? 'Processing...' : (authMode === 'login' ? 'Sign In' : 'Sign Up')}
              </button>
            </form>
            <p className="toggle-auth">
              {authMode === 'login' ? "Don't have an account? " : "Already have an account? "}
              <span onClick={() => { setAuthMode(authMode === 'login' ? 'signup' : 'login'); setAuthError(''); }}>
                {authMode === 'login' ? 'Sign Up' : 'Sign In'}
              </span>
            </p>
          </div>
        )}

        {view === 'dashboard' && (
          <div className="dashboard animate-fade-in">
            <div className="stats-row">
              <div className="glass-card stat-box"><h3> {stats.photo_count} </h3> <p>Photos</p></div>
              <div className="glass-card stat-box"><h3> {stats.person_count} </h3> <p>Faces Recognized</p></div>
              <div className="glass-card stat-box"><h3> {stats.history_count} </h3> <p>Events Grouped</p></div>
            </div>

            <div className="gallery-section">
              <div className="section-header">
                <h2>Your Collection</h2>
                <div className="upload-btn-wrapper">
                  <button className="btn-primary" disabled={uploading}>
                    {uploading ? 'Uploading...' : 'Upload New'}
                  </button>
                  <input type="file" onChange={handleUpload} accept="image/*" disabled={uploading} />
                </div>
              </div>
              <div className="photo-grid">
                {photos.length > 0 ? photos.map(p => (
                  <div key={p.id} className="photo-card glass-card">
                    <img
                      src={`${API_BASE}/dashboard/media/${p.filename}`}
                      alt={p.filename}
                      className="photo-img"
                      onError={(e) => e.target.src = 'https://via.placeholder.com/300x200?text=Photo+Error'}
                    />
                    <div className="photo-info">
                      <p className="photo-name">{p.filename.split('_').slice(2).join('_')}</p>
                      <small>{new Date(p.upload_date).toLocaleDateString()}</small>
                    </div>
                  </div>
                )) : (
                  <div className="empty-state glass-card">
                    <p>No photos yet. Start by uploading some!</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {token && (
        <div className={`chat-widget ${chatOpen ? 'open' : ''}`}>
          <button className="chat-toggle btn-primary" onClick={() => setChatOpen(!chatOpen)}>
            {chatOpen ? '✕' : '💬 Ask AI'}
          </button>
          {chatOpen && (
            <div className="chat-window glass-card animate-fade-in">
              <div className="chat-header">Assistant</div>
              <div className="chat-messages">
                {messages.map((m, idx) => (
                  <div key={idx} className={`msg ${m.role}`}>
                    {m.content}
                  </div>
                ))}
                {chatLoading && <div className="msg bot">...</div>}
              </div>
              <form className="chat-input" onSubmit={handleSendMessage}>
                <input
                  type="text"
                  placeholder="Type a message..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={chatLoading}
                />
              </form>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;

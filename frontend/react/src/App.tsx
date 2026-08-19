import React, { useState, useRef } from 'react';

interface ThreatData {
  risk_score: number;
  risk_level: string;
  fast_path_alert: boolean;
  latest_transcript: string;
  detected_tactics: string[];
  explanation: string;
  recommended_action: string;
}

export default function App() {
  const [isLive, setIsLive] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [testInput, setTestInput] = useState('please transfer money to a safe account immediately');
  const wsRef = useRef<WebSocket | null>(null);

  const [threat, setThreat] = useState<ThreatData>({
    risk_score: 0.12,
    risk_level: 'LOW',
    fast_path_alert: false,
    latest_transcript: 'Call connected. Monitoring active stream...',
    detected_tactics: [],
    explanation: 'No suspicious activity detected yet.',
    recommended_action: 'Continue call safely.'
  });

  const startLiveSession = async () => {
    const res = await fetch('http://localhost:8000/api/v1/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 'demo_user', device_type: 'desktop' })
    });
    const data = await res.json();
    setSessionId(data.session_id);

    const ws = new WebSocket(`ws://localhost:8000${data.ws_endpoint}`);
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      setThreat({
        risk_score: update.risk_score,
        risk_level: update.risk_level,
        fast_path_alert: update.fast_path_alert,
        latest_transcript: update.latest_transcript,
        detected_tactics: update.detected_tactics,
        explanation: update.explanation,
        recommended_action: update.recommended_action
      });
    };
    wsRef.current = ws;
    setIsLive(true);
  };

  const stopLiveSession = () => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsLive(false);
  };

  const sendTestPhrase = () => {
    wsRef.current?.send(JSON.stringify({ transcript: testInput }));
  };

  const copySessionId = () => {
    if (!sessionId) return;
    navigator.clipboard.writeText(sessionId);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#030712', color: '#f3f4f6', padding: '2rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ fontSize: '2rem' }}>🛡️</div>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0, background: 'linear-gradient(to right, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Sentinel AI
            </h1>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af', margin: 0 }}>Real-Time Live Call Scam Shield</p>
            {sessionId && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontFamily: 'monospace' }}>
                  Session: {sessionId}
                </span>
                <button
                  onClick={copySessionId}
                  style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem', borderRadius: '0.35rem', border: '1px solid #1e293b', backgroundColor: '#0f172a', color: '#9ca3af', cursor: 'pointer' }}
                >
                  {copied ? 'Copied!' : 'Copy Session ID'}
                </button>
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={isLive ? stopLiveSession : startLiveSession}
            style={{
              padding: '0.625rem 1.25rem',
              borderRadius: '0.5rem',
              fontWeight: '600',
              cursor: 'pointer',
              border: 'none',
              backgroundColor: isLive ? '#ef4444' : '#10b981',
              color: '#ffffff',
              boxShadow: isLive ? '0 0 15px rgba(239, 68, 68, 0.4)' : '0 0 15px rgba(16, 185, 129, 0.4)'
            }}
          >
            {isLive ? 'Stop Monitoring' : 'Start Live Call Shield'}
          </button>
        </div>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>

        <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: '#38bdf8' }}>
            Live Stream Diagnostics
          </h2>

          <div style={{ marginBottom: '1.5rem', padding: '1.25rem', borderRadius: '0.75rem', backgroundColor: 'rgba(17, 24, 39, 0.9)', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem', color: '#9ca3af' }}>Computed Scam Probability</span>
              <span style={{ fontWeight: 'bold', color: threat.risk_score > 0.7 ? '#ef4444' : threat.risk_score > 0.4 ? '#f59e0b' : '#10b981' }}>
                {(threat.risk_score * 100).toFixed(0)}% [{threat.risk_level}]
              </span>
            </div>
            <div style={{ width: '100%', height: '12px', backgroundColor: '#1f2937', borderRadius: '6px', overflow: 'hidden' }}>
              <div style={{
                width: `${threat.risk_score * 100}%`,
                height: '100%',
                backgroundColor: threat.risk_score > 0.7 ? '#ef4444' : threat.risk_score > 0.4 ? '#f59e0b' : '#10b981',
                transition: 'width 0.5s ease-in-out'
              }} />
            </div>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '0.5rem' }}>Latest Live Transcript Segment</h3>
            <div style={{ padding: '1rem', backgroundColor: '#0f172a', borderRadius: '0.5rem', border: '1px solid #1e293b', fontFamily: 'monospace', fontSize: '0.9rem', color: '#e2e8f0' }}>
              {threat.latest_transcript}
            </div>
          </div>

          {isLive && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                style={{ flex: 1, padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #1e293b', backgroundColor: '#0f172a', color: 'white' }}
              />
              <button
                onClick={sendTestPhrase}
                style={{ padding: '0.75rem 1.25rem', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '0.5rem', fontWeight: 600, cursor: 'pointer' }}
              >
                Send to Backend
              </button>
            </div>
          )}
        </div>

        <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: '#818cf8' }}>
            Supervisor Agent Analysis
          </h2>

          {threat.fast_path_alert && (
            <div className="glass-alert pulse-red" style={{ padding: '1rem', borderRadius: '0.75rem', marginBottom: '1.5rem', color: '#fca5a5' }}>
              <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '0.25rem' }}>⚠️ FAST-PATH EMERGENCY ALERT</div>
              <div>OTP / Verification Code theft attempt detected in under 200ms.</div>
            </div>
          )}

          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '0.5rem' }}>Detected Fraud Tactics</h3>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {threat.detected_tactics.length > 0 ? (
                threat.detected_tactics.map((tactic, idx) => (
                  <span key={idx} style={{ padding: '0.25rem 0.75rem', backgroundColor: 'rgba(239, 68, 68, 0.2)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '1rem', fontSize: '0.8rem', color: '#fca5a5' }}>
                    {tactic}
                  </span>
                ))
              ) : (
                <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>No tactics flagged yet</span>
              )}
            </div>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '0.5rem' }}>Reasoning Synthesis</h3>
            <p style={{ fontSize: '0.95rem', color: '#d1d5db', lineHeight: '1.5' }}>{threat.explanation}</p>
          </div>

          <div style={{ padding: '1rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '0.75rem' }}>
            <h3 style={{ fontSize: '0.875rem', color: '#6ee7b7', marginBottom: '0.25rem', fontWeight: 'bold' }}>Recommended User Safety Action</h3>
            <p style={{ fontSize: '0.95rem', color: '#a7f3d0', margin: 0, fontWeight: '500' }}>{threat.recommended_action}</p>
          </div>
        </div>

      </div>
    </div>
  );
}
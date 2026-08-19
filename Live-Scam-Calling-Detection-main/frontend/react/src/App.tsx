import React, { useState, useEffect } from 'react';

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
  const [threat, setThreat] = useState<ThreatData>({
    risk_score: 0.12,
    risk_level: 'LOW',
    fast_path_alert: false,
    latest_transcript: 'Call connected. Monitoring active stream...',
    detected_tactics: [],
    explanation: 'No suspicious activity detected yet.',
    recommended_action: 'Continue call safely.'
  });

  const [simulatedTranscripts, setSimulatedTranscripts] = useState<string[]>([
    "Hello? I am calling from Chase Bank Fraud Prevention.",
    "We noticed an urgent attempt to transfer $2,500 from your account.",
    "To stop this transfer, please tell me the 6-digit verification code sent to your phone immediately."
  ]);
  const [transcriptIndex, setTranscriptIndex] = useState(0);

  const startLiveSession = () => {
    setIsLive(true);
    setSessionId(`sess_${Math.random().toString(36).substr(2, 9)}`);
  };

  const stopLiveSession = () => {
    setIsLive(false);
  };

  const injectSimulatedPhrase = () => {
    if (transcriptIndex < simulatedTranscripts.length) {
      const text = simulatedTranscripts[transcriptIndex];
      setTranscriptIndex(prev => prev + 1);

      // Simulate Fast-Path + Supervisor Evaluation
      if (text.includes("6-digit verification code")) {
        setThreat({
          risk_score: 0.95,
          risk_level: 'CRITICAL',
          fast_path_alert: true,
          latest_transcript: text,
          detected_tactics: ['OTP_THEFT', 'IMPERSONATION_BANK', 'HIGH_URGENCY'],
          explanation: 'CRITICAL THREAT: Caller requested a 6-digit OTP code claiming to be your bank.',
          recommended_action: 'DO NOT SHARE CODE. HANG UP IMMEDIATELY!'
        });
      } else if (text.includes("transfer $2,500")) {
        setThreat({
          risk_score: 0.65,
          risk_level: 'HIGH',
          fast_path_alert: false,
          latest_transcript: text,
          detected_tactics: ['IMPERSONATION_BANK', 'URGENCY'],
          explanation: 'Caller claiming financial threat requiring urgent action.',
          recommended_action: 'Verify caller identity independently before taking action.'
        });
      } else {
        setThreat({
          risk_score: 0.25,
          risk_level: 'LOW',
          fast_path_alert: false,
          latest_transcript: text,
          detected_tactics: ['BANK_MENTION'],
          explanation: 'Caller introduced bank identity.',
          recommended_action: 'Listen carefully.'
        });
      }
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#030712', color: '#f3f4f6', padding: '2rem' }}>
      {/* Top Navbar */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ fontSize: '2rem' }}>🛡️</div>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0, background: 'linear-gradient(to right, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Sentinel AI
            </h1>
            <p style={{ fontSize: '0.875rem', color: '#9ca3af', margin: 0 }}>Real-Time Live Call Scam Shield</p>
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

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        
        {/* Left Column: Real-Time Stream & Risk Meter */}
        <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: '#38bdf8' }}>
            Live Stream Diagnostics
          </h2>

          {/* Risk Score Gauge */}
          <div style={{ marginBottom: '1.5rem', padding: '1.25rem', borderRadius: '0.75rem', backgroundColor: 'rgba(17, 24, 39, 0.9)', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem', color: '#9ca3af' }}>Computed Scam Probability</span>
              <span style={{ fontWeight: 'bold', color: threat.risk_score > 0.7 ? '#ef4444' : threat.risk_score > 0.4 ? '#f59e0b' : '#10b981' }}>
                {(threat.risk_score * 100).toFixed(0)}% [{threat.risk_level}]
              </span>
            </div>

            {/* Progress Bar */}
            <div style={{ width: '100%', height: '12px', backgroundColor: '#1f2937', borderRadius: '6px', overflow: 'hidden' }}>
              <div style={{ 
                width: `${threat.risk_score * 100}%`, 
                height: '100%', 
                backgroundColor: threat.risk_score > 0.7 ? '#ef4444' : threat.risk_score > 0.4 ? '#f59e0b' : '#10b981',
                transition: 'width 0.5s ease-in-out'
              }} />
            </div>
          </div>

          {/* Live Transcript Stream Box */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '0.5rem' }}>Latest Live Transcript Segment</h3>
            <div style={{ padding: '1rem', backgroundColor: '#0f172a', borderRadius: '0.5rem', border: '1px solid #1e293b', fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: '#e2e8f0' }}>
              {threat.latest_transcript}
            </div>
          </div>

          {/* Simulation Controls */}
          {isLive && (
            <button 
              onClick={injectSimulatedPhrase}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              Simulate Incoming Call Phrase ({transcriptIndex + 1}/{simulatedTranscripts.length})
            </button>
          )}
        </div>

        {/* Right Column: Threat Assessment & Mitigations */}
        <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: '#818cf8' }}>
            Supervisor Agent Analysis
          </h2>

          {/* Emergency Alert Banner if Critical */}
          {threat.fast_path_alert && (
            <div className="glass-alert pulse-red" style={{ padding: '1rem', borderRadius: '0.75rem', marginBottom: '1.5rem', color: '#fca5a5' }}>
              <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '0.25rem' }}>⚠️ FAST-PATH EMERGENCY ALERT</div>
              <div>OTP / Verification Code theft attempt detected in under 200ms.</div>
            </div>
          )}

          {/* Detected Tactics */}
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

          {/* Reasoning Explanation */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '0.5rem' }}>Reasoning Synthesis</h3>
            <p style={{ fontSize: '0.95rem', color: '#d1d5db', lineHeight: '1.5' }}>{threat.explanation}</p>
          </div>

          {/* Recommended Action */}
          <div style={{ padding: '1rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '0.75rem' }}>
            <h3 style={{ fontSize: '0.875rem', color: '#6ee7b7', marginBottom: '0.25rem', fontWeight: 'bold' }}>Recommended User Safety Action</h3>
            <p style={{ fontSize: '0.95rem', color: '#a7f3d0', margin: 0, fontWeight: '500' }}>{threat.recommended_action}</p>
          </div>
        </div>

      </div>
    </div>
  );
}

import React, { useState, useEffect, useRef } from 'react';

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
  const [engine, setEngine] = useState<'webspeech' | 'scribe'>('webspeech');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [testInput, setTestInput] = useState('please transfer money to a safe account immediately');

  const [threat, setThreat] = useState<ThreatData>({
    risk_score: 0.0,
    risk_level: 'LOW',
    fast_path_alert: false,
    latest_transcript: 'Call connected. Monitoring active stream...',
    detected_tactics: [],
    explanation: 'No suspicious activity detected yet.',
    recommended_action: 'Continue call safely.'
  });

  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const cleanup = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  const float32ToInt16 = (buffer: Float32Array) => {
    let l = buffer.length;
    const buf = new Int16Array(l);
    while (l--) {
      buf[l] = Math.max(-1, Math.min(1, buffer[l])) * 0x7FFF;
    }
    return buf.buffer;
  };

  const bufferToBase64 = (buffer: ArrayBuffer) => {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
  };

  const startLiveSession = async () => {
    setIsLive(true);
    const newSessionId = `sess_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);
    
    // 1. Connect WebSocket to FastAPI
    const ws = new WebSocket(`ws://localhost:8000/ws/live/${newSessionId}`);
    wsRef.current = ws;
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'threat_update') {
        setThreat(data);
      }
    };

    ws.onopen = async () => {
      if (engine === 'webspeech') {
        // Path 1: Native Web Speech API
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!SpeechRecognition) {
          alert("Web Speech API not supported in this browser. Try Scribe v2 mode.");
          return;
        }
        
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false; // Send only final phrases
        
        recognition.onresult = (event: any) => {
          const resultIndex = event.resultIndex;
          const transcript = event.results[resultIndex][0].transcript;
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ transcript }));
          }
        };
        
        recognition.start();
        recognitionRef.current = recognition;
        
      } else {
        // Path 2: Scribe v2 (Raw Audio via WS)
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          streamRef.current = stream;
          
          const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
          audioContextRef.current = audioContext;
          
          const source = audioContext.createMediaStreamSource(stream);
          const processor = audioContext.createScriptProcessor(4096, 1, 1);
          
          source.connect(processor);
          
          // Connect to destination through a muted GainNode to prevent feedback loop
          // (Required in some browsers for onaudioprocess to fire)
          const gainNode = audioContext.createGain();
          gainNode.gain.value = 0;
          processor.connect(gainNode);
          gainNode.connect(audioContext.destination);
          
          processor.onaudioprocess = (e) => {
            if (ws.readyState !== WebSocket.OPEN) return;
            
            const float32Data = e.inputBuffer.getChannelData(0);
            const int16Buffer = float32ToInt16(float32Data);
            const base64Audio = bufferToBase64(int16Buffer);
            
            ws.send(JSON.stringify({ audio_b64: base64Audio }));
          };
          
        } catch (err) {
          console.error("Error accessing microphone:", err);
          alert("Microphone access denied.");
        }
      }
    };
  };

  const stopLiveSession = () => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsLive(false);
    cleanup();
  };

  useEffect(() => {
    return cleanup;
  }, []);

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
          
          <select 
            value={engine} 
            onChange={(e) => setEngine(e.target.value as 'webspeech' | 'scribe')}
            disabled={isLive}
            style={{ padding: '0.625rem', borderRadius: '0.5rem', backgroundColor: '#1f2937', color: 'white', border: '1px solid #374151', cursor: isLive ? 'not-allowed' : 'pointer' }}
          >
            <option value="webspeech">Native Web Speech API (Local)</option>
            <option value="scribe">ElevenLabs Scribe v2 (Cloud)</option>
          </select>

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
        
        {/* Left Column: Real-Time Stream & Risk Meter */}
        <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '1rem', backgroundColor: 'rgba(17, 24, 39, 0.5)', border: '1px solid #1f2937' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: '#38bdf8' }}>
            Live Stream Diagnostics ({engine === 'webspeech' ? 'Web Speech API' : 'Scribe v2'})
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
            <div style={{ padding: '1rem', backgroundColor: '#0f172a', borderRadius: '0.5rem', border: '1px solid #1e293b', fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: '#e2e8f0', minHeight: '80px' }}>
              {threat.latest_transcript}
            </div>
            {isLive && sessionId && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontFamily: 'monospace' }}>
                  Session: {sessionId}
                </span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(sessionId);
                    alert('Copied Session ID!');
                  }}
                  style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem', borderRadius: '0.35rem', border: '1px solid #1e293b', backgroundColor: '#0f172a', color: '#9ca3af', cursor: 'pointer' }}
                >
                  Copy Session ID
                </button>
              </div>
            )}
          </div>
          
          {/* Manual Input Override */}
          {isLive && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                id="testInputOverride"
                placeholder="Or type a phrase manually..."
                style={{ flex: 1, padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #1e293b', backgroundColor: '#0f172a', color: 'white' }}
              />
              <button
                onClick={() => {
                  const input = document.getElementById('testInputOverride') as HTMLInputElement;
                  if (input && input.value.trim() && wsRef.current?.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({ transcript: input.value }));
                    input.value = '';
                  }
                }}
                style={{ padding: '0.75rem 1.25rem', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '0.5rem', fontWeight: 600, cursor: 'pointer' }}
              >
                Send to Backend
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Threat Assessment & Mitigations */}
        <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '1rem', backgroundColor: 'rgba(17, 24, 39, 0.5)', border: '1px solid #1f2937' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: '#818cf8' }}>
            Supervisor Agent Analysis
          </h2>

          {threat.fast_path_alert && (
            <div className="glass-alert pulse-red" style={{ padding: '1rem', borderRadius: '0.75rem', marginBottom: '1.5rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5' }}>
              <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '0.25rem' }}>⚠️ FAST-PATH EMERGENCY ALERT</div>
              <div>OTP / Verification Code theft attempt detected in under 200ms.</div>
            </div>
          )}

          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '0.5rem' }}>Detected Fraud Tactics</h3>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {threat.detected_tactics && threat.detected_tactics.length > 0 ? (
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
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

interface TranscriptItem {
  id: string;
  text: string;
  timestamp: string;
  isScam?: boolean;
}

export default function App() {
  const [isLive, setIsLive] = useState(false);
  const [engine, setEngine] = useState<'webspeech' | 'scribe'>('webspeech');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [liveInterim, setLiveInterim] = useState('');
  const [transcriptHistory, setTranscriptHistory] = useState<TranscriptItem[]>([]);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [micVolume, setMicVolume] = useState(0);

  const [threat, setThreat] = useState<ThreatData>({
    risk_score: 0.0,
    risk_level: 'LOW',
    fast_path_alert: false,
    latest_transcript: 'Call shield ready. Click "Start Live Call Shield" to begin listening.',
    detected_tactics: [],
    explanation: 'No suspicious activity detected yet.',
    recommended_action: 'Monitoring active. Speak normally into your microphone.'
  });

  const wsRef = useRef<WebSocket | null>(null);
  const isLiveRef = useRef(false);
  const recognitionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animFrameRef = useRef<number | null>(null);

  isLiveRef.current = isLive;

  const cleanup = () => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {}
      recognitionRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch (e) {}
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsRecognizing(false);
    setMicVolume(0);
  };

  const float32ToInt16 = (buffer: Float32Array) => {
    let l = buffer.length;
    const buf = new Int16Array(l);
    while (l--) {
      buf[l] = Math.max(-1, Math.min(1, buffer[l])) * 0x7fff;
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

  const copySessionId = () => {
    if (sessionId) {
      navigator.clipboard.writeText(sessionId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const sendPhraseToBackend = (text: string) => {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();

    // Append to local history immediately
    const newItem: TranscriptItem = {
      id: Math.random().toString(36).substring(2, 9),
      text: cleanText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };
    setTranscriptHistory((prev) => [newItem, ...prev.slice(0, 19)]);
    setLiveInterim('');

    // Send to backend via WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ transcript: cleanText }));
    }
  };

  const startLiveSession = async () => {
    setIsLive(true);
    isLiveRef.current = true;
    const newSessionId = `sess_${Math.random().toString(36).substring(2, 9)}`;
    setSessionId(newSessionId);

    // 1. Connect WebSocket to FastAPI
    const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws/live/${newSessionId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'threat_update') {
          setThreat(data);
          // Mark latest transcript item
          if (data.risk_score >= 0.45) {
            setTranscriptHistory((prev) =>
              prev.map((item, idx) => (idx === 0 ? { ...item, isScam: true } : item))
            );
          }
        }
      } catch (err) {
        console.error('Error parsing backend message:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };

    ws.onclose = () => {
      if (isLiveRef.current) {
        stopLiveSession();
      }
    };

    ws.onopen = async () => {
      if (engine === 'webspeech') {
        // Path 1: Native Web Speech API
        const SpeechRecognition =
          (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

        if (!SpeechRecognition) {
          alert('Web Speech API is not supported in this browser. Please use Chrome or switch to Scribe v2 mode.');
          return;
        }

        const setupRecognition = () => {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'en-US';
          recognition.maxAlternatives = 1;

          recognition.onstart = () => {
            setIsRecognizing(true);
          };

          recognition.onresult = (event: any) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
              const transcriptPiece = event.results[i][0].transcript;
              if (event.results[i].isFinal) {
                sendPhraseToBackend(transcriptPiece);
              } else {
                interim += transcriptPiece;
              }
            }
            if (interim) {
              setLiveInterim(interim);
            }
          };

          recognition.onerror = (event: any) => {
            console.warn('Speech recognition warning/error:', event.error);
            if (event.error === 'not-allowed') {
              alert('Microphone access was denied. Please allow microphone access in your browser settings.');
              stopLiveSession();
            }
          };

          recognition.onend = () => {
            setIsRecognizing(false);
            // AUTO RESTART: Chrome stops recognition after periods of silence.
            // If the user hasn't clicked stop, restart immediately!
            if (isLiveRef.current) {
              try {
                recognition.start();
              } catch (e) {
                // If start fails, recreate recognition
                setTimeout(() => {
                  if (isLiveRef.current) setupRecognition();
                }, 300);
              }
            }
          };

          try {
            recognition.start();
            recognitionRef.current = recognition;
          } catch (err) {
            console.error('Failed to start speech recognition:', err);
          }
        };

        setupRecognition();

        // Also setup a lightweight audio visualizer so user sees mic activity
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          streamRef.current = stream;
          const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
          audioContextRef.current = audioCtx;
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 256;
          const source = audioCtx.createMediaStreamSource(stream);
          source.connect(analyser);

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          const updateVolume = () => {
            if (!isLiveRef.current) return;
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
            const avg = sum / dataArray.length;
            setMicVolume(Math.min(100, Math.round(avg * 2.5)));
            animFrameRef.current = requestAnimationFrame(updateVolume);
          };
          updateVolume();
        } catch (e) {
          console.warn('Visualizer stream optional error:', e);
        }
      } else {
        // Path 2: Scribe v2 (Raw Audio streaming via WS)
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          streamRef.current = stream;

          const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
            sampleRate: 16000
          });
          audioContextRef.current = audioContext;

          const source = audioContext.createMediaStreamSource(stream);
          const processor = audioContext.createScriptProcessor(4096, 1, 1);
          const analyser = audioContext.createAnalyser();
          analyser.fftSize = 256;

          source.connect(analyser);
          source.connect(processor);

          const gainNode = audioContext.createGain();
          gainNode.gain.value = 0;
          processor.connect(gainNode);
          gainNode.connect(audioContext.destination);

          setIsRecognizing(true);

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          const updateVolume = () => {
            if (!isLiveRef.current) return;
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
            const avg = sum / dataArray.length;
            setMicVolume(Math.min(100, Math.round(avg * 2.5)));
            animFrameRef.current = requestAnimationFrame(updateVolume);
          };
          updateVolume();

          processor.onaudioprocess = (e) => {
            if (ws.readyState !== WebSocket.OPEN) return;

            const float32Data = e.inputBuffer.getChannelData(0);
            const int16Buffer = float32ToInt16(float32Data);
            const base64Audio = bufferToBase64(int16Buffer);

            ws.send(JSON.stringify({ audio_b64: base64Audio }));
          };
        } catch (err) {
          console.error('Error accessing microphone:', err);
          alert('Microphone access denied. Please grant permission in your browser.');
          stopLiveSession();
        }
      }
    };
  };

  const stopLiveSession = () => {
    setIsLive(false);
    isLiveRef.current = false;
    cleanup();
  };

  useEffect(() => {
    return cleanup;
  }, []);

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#030712', color: '#f3f4f6', padding: '1.5rem', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Header Bar */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid #1f2937', paddingBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ fontSize: '2.25rem' }}>🛡️</div>
          <div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: '800', margin: 0, background: 'linear-gradient(to right, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Sentinel AI
            </h1>
            <p style={{ fontSize: '0.85rem', color: '#9ca3af', margin: '0.1rem 0 0 0' }}>Real-Time Live Call Scam Shield & Threat Detector</p>
            {sessionId && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.35rem' }}>
                <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontFamily: 'monospace', backgroundColor: '#0f172a', padding: '0.15rem 0.4rem', borderRadius: '0.25rem', border: '1px solid #1e293b' }}>
                  {sessionId}
                </span>
                <button
                  onClick={copySessionId}
                  style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem', borderRadius: '0.35rem', border: '1px solid #1e293b', backgroundColor: '#1e293b', color: '#9ca3af', cursor: 'pointer' }}
                >
                  {copied ? '✅ Copied' : '📋 Copy ID'}
                </button>
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <select
            value={engine}
            onChange={(e) => setEngine(e.target.value as 'webspeech' | 'scribe')}
            disabled={isLive}
            style={{ padding: '0.625rem 0.85rem', borderRadius: '0.5rem', backgroundColor: '#111827', color: '#e5e7eb', border: '1px solid #374151', cursor: isLive ? 'not-allowed' : 'pointer', fontSize: '0.875rem' }}
          >
            <option value="webspeech">⚡ Native Web Speech (Instant / Zero-Lag)</option>
            <option value="scribe">☁️ ElevenLabs Scribe v2 (Cloud)</option>
          </select>

          <button
            onClick={isLive ? stopLiveSession : startLiveSession}
            style={{
              padding: '0.65rem 1.4rem',
              borderRadius: '0.5rem',
              fontWeight: '700',
              cursor: 'pointer',
              border: 'none',
              fontSize: '0.95rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              backgroundColor: isLive ? '#ef4444' : '#10b981',
              color: '#ffffff',
              boxShadow: isLive ? '0 0 20px rgba(239, 68, 68, 0.45)' : '0 0 20px rgba(16, 185, 129, 0.35)',
              transition: 'all 0.2s ease'
            }}
          >
            {isLive ? (
              <>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#ffffff', display: 'inline-block', animation: 'pulse 1s infinite' }} />
                Stop Shield
              </>
            ) : (
              <>
                <span>🎙️</span> Start Live Call Shield
              </>
            )}
          </button>
        </div>
      </header>

      {/* Live Mic Activity Banner when Active */}
      {isLive && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 1.25rem', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '0.75rem', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.25rem' }}>🎙️</span>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#10b981' }}>
                  {isRecognizing ? 'Microphone Active & Listening...' : 'Connecting Audio Stream...'}
                </span>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: isRecognizing ? '#10b981' : '#f59e0b', display: 'inline-block' }} />
              </div>
              <p style={{ margin: 0, fontSize: '0.75rem', color: '#9ca3af' }}>Speak into your mic to test real-time detection</p>
            </div>
          </div>

          {/* Realtime Audio Volume Meter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '160px' }}>
            <span style={{ fontSize: '0.7rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Volume</span>
            <div style={{ flex: 1, height: '8px', backgroundColor: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${micVolume}%`, height: '100%', backgroundColor: micVolume > 60 ? '#ef4444' : micVolume > 25 ? '#10b981' : '#38bdf8', transition: 'width 0.1s ease' }} />
            </div>
          </div>
        </div>
      )}

      {/* Main Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '1.5rem' }}>
        {/* Left Column: Live Audio, Speech Stream, History & Manual Inputs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Scam Probability Meter Card */}
          <div style={{ padding: '1.25rem', borderRadius: '0.85rem', backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
              <span style={{ fontSize: '0.875rem', color: '#9ca3af', fontWeight: 500 }}>Live Threat Score</span>
              <span style={{ fontWeight: 800, fontSize: '1.1rem', color: threat.risk_score > 0.7 ? '#ef4444' : threat.risk_score > 0.4 ? '#f59e0b' : '#10b981' }}>
                {(threat.risk_score * 100).toFixed(0)}% [{threat.risk_level}]
              </span>
            </div>
            <div style={{ width: '100%', height: '14px', backgroundColor: '#1e293b', borderRadius: '7px', overflow: 'hidden', border: '1px solid #334155' }}>
              <div
                style={{
                  width: `${threat.risk_score * 100}%`,
                  height: '100%',
                  backgroundColor: threat.risk_score > 0.7 ? '#ef4444' : threat.risk_score > 0.4 ? '#f59e0b' : '#10b981',
                  transition: 'width 0.4s ease-in-out',
                  boxShadow: threat.risk_score > 0.7 ? '0 0 10px #ef4444' : 'none'
                }}
              />
            </div>
          </div>

          {/* Live Transcript Display */}
          <div style={{ padding: '1.25rem', borderRadius: '0.85rem', backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <h3 style={{ fontSize: '0.875rem', color: '#38bdf8', margin: 0, fontWeight: 600 }}>
                💬 Live Speech-to-Text Stream
              </h3>
              {liveInterim && (
                <span style={{ fontSize: '0.75rem', color: '#a855f7', animation: 'pulse 1s infinite' }}>
                  ● Transcribing...
                </span>
              )}
            </div>

            {/* Active Speech Box */}
            <div
              style={{
                padding: '1rem',
                backgroundColor: '#030712',
                borderRadius: '0.5rem',
                border: '1px solid #1e293b',
                minHeight: '75px',
                fontSize: '0.95rem',
                color: '#e2e8f0',
                lineHeight: 1.5,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center'
              }}
            >
              {liveInterim ? (
                <span style={{ color: '#c084fc', fontStyle: 'italic' }}>"{liveInterim}"</span>
              ) : transcriptHistory.length > 0 ? (
                <span>"{transcriptHistory[0].text}"</span>
              ) : (
                <span style={{ color: '#64748b' }}>
                  {isLive ? 'Listening... say something into your mic!' : 'Shield is stopped. Click Start above.'}
                </span>
              )}
            </div>

            {/* Transcript Log History */}
            {transcriptHistory.length > 1 && (
              <div style={{ marginTop: '1rem' }}>
                <h4 style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', margin: '0 0 0.5rem 0', letterSpacing: '0.05em' }}>
                  Recent Spoken Phrases
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', maxHeight: '140px', overflowY: 'auto' }}>
                  {transcriptHistory.slice(1, 6).map((item) => (
                    <div
                      key={item.id}
                      style={{
                        fontSize: '0.82rem',
                        padding: '0.4rem 0.6rem',
                        borderRadius: '0.35rem',
                        backgroundColor: item.isScam ? 'rgba(239, 68, 68, 0.15)' : '#111827',
                        borderLeft: item.isScam ? '3px solid #ef4444' : '3px solid #3b82f6',
                        color: '#d1d5db',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <span>{item.text}</span>
                      <span style={{ fontSize: '0.7rem', color: '#6b7280' }}>{item.timestamp}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Quick 1-Click Scam Simulation Scenarios */}
          <div style={{ padding: '1.25rem', borderRadius: '0.85rem', backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
            <h3 style={{ fontSize: '0.85rem', color: '#9ca3af', margin: '0 0 0.75rem 0', fontWeight: 600 }}>
              🧪 Instant Scam Simulation Buttons (1-Click Test)
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <button
                onClick={() => sendPhraseToBackend('This is Chase Bank fraud prevention. Please share your 6-digit OTP code immediately.')}
                disabled={!isLive}
                style={{ padding: '0.6rem 0.8rem', backgroundColor: '#7f1d1d', border: '1px solid #991b1b', borderRadius: '0.5rem', color: '#fecaca', fontSize: '0.78rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5, fontWeight: 600 }}
              >
                🚨 Bank OTP Theft
              </button>
              <button
                onClick={() => sendPhraseToBackend('Urgent: You must transfer all funds to a safe government holding account right now.')}
                disabled={!isLive}
                style={{ padding: '0.6rem 0.8rem', backgroundColor: '#78350f', border: '1px solid #92400e', borderRadius: '0.5rem', color: '#fef3c7', fontSize: '0.78rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5, fontWeight: 600 }}
              >
                ⚠️ Safe Account Transfer
              </button>
              <button
                onClick={() => sendPhraseToBackend('This is Microsoft support. Your computer has viruses, buy gift cards to pay our technician.')}
                disabled={!isLive}
                style={{ padding: '0.6rem 0.8rem', backgroundColor: '#581c87', border: '1px solid #6b21a8', borderRadius: '0.5rem', color: '#f3e8ff', fontSize: '0.78rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5, fontWeight: 600 }}
              >
                💻 Tech Support / Gift Card
              </button>
              <button
                onClick={() => sendPhraseToBackend('Hi there, I am just calling to see how you are doing today and if you want to get lunch.')}
                disabled={!isLive}
                style={{ padding: '0.6rem 0.8rem', backgroundColor: '#064e3b', border: '1px solid #065f46', borderRadius: '0.5rem', color: '#a7f3d0', fontSize: '0.78rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5, fontWeight: 600 }}
              >
                ✅ Safe Normal Call
              </button>
            </div>

            {/* Custom Text Input */}
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
              <input
                id="testInputOverride"
                placeholder="Or type any phrase manually..."
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const input = e.currentTarget;
                    if (input && input.value.trim()) {
                      sendPhraseToBackend(input.value);
                      input.value = '';
                    }
                  }
                }}
                style={{ flex: 1, padding: '0.6rem 0.8rem', borderRadius: '0.5rem', border: '1px solid #1e293b', backgroundColor: '#030712', color: 'white', fontSize: '0.85rem' }}
              />
              <button
                onClick={() => {
                  const input = document.getElementById('testInputOverride') as HTMLInputElement;
                  if (input && input.value.trim()) {
                    sendPhraseToBackend(input.value);
                    input.value = '';
                  }
                }}
                disabled={!isLive}
                style={{ padding: '0.6rem 1rem', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '0.5rem', fontWeight: 600, fontSize: '0.85rem', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5 }}
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Threat Assessment & Mitigations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Fast-Path Critical Alert Card */}
          {threat.fast_path_alert && (
            <div
              style={{
                padding: '1.25rem',
                borderRadius: '0.85rem',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                border: '2px solid #ef4444',
                color: '#fca5a5',
                boxShadow: '0 0 25px rgba(239, 68, 68, 0.35)',
                animation: 'pulse 1.5s infinite'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 800, fontSize: '1.15rem', color: '#ef4444', marginBottom: '0.35rem' }}>
                <span>🚨</span> FAST-PATH EMERGENCY THREAT DETECTED
              </div>
              <div style={{ fontSize: '0.9rem', color: '#fee2e2' }}>
                OTP / Two-Factor Authentication Theft intercepted in sub-200ms. Immediate action recommended!
              </div>
            </div>
          )}

          {/* Supervisor Agent Analysis Card */}
          <div style={{ padding: '1.25rem', borderRadius: '0.85rem', backgroundColor: '#0f172a', border: '1px solid #1e293b', flex: 1 }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: '700', marginBottom: '1rem', color: '#818cf8', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>🧠</span> Sentinel Supervisor Analysis
            </h2>

            <div style={{ marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '0.8rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
                Detected Fraud Tactics
              </h3>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {threat.detected_tactics && threat.detected_tactics.length > 0 ? (
                  threat.detected_tactics.map((tactic, idx) => (
                    <span
                      key={idx}
                      style={{
                        padding: '0.3rem 0.8rem',
                        backgroundColor: 'rgba(239, 68, 68, 0.2)',
                        border: '1px solid rgba(239, 68, 68, 0.5)',
                        borderRadius: '1rem',
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        color: '#fca5a5',
                        letterSpacing: '0.02em'
                      }}
                    >
                      ⚡ {tactic}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>No scam tactics identified yet</span>
                )}
              </div>
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '0.8rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
                Reasoning & Evidence
              </h3>
              <p style={{ fontSize: '0.92rem', color: '#d1d5db', lineHeight: 1.5, backgroundColor: '#030712', padding: '0.85rem', borderRadius: '0.5rem', border: '1px solid #1e293b', margin: 0 }}>
                {threat.explanation || 'Listening to conversation stream for deceptive patterns...'}
              </p>
            </div>

            <div>
              <h3 style={{ fontSize: '0.8rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
                Recommended User Action
              </h3>
              <div
                style={{
                  padding: '0.85rem 1rem',
                  backgroundColor: threat.risk_score >= 0.45 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.1)',
                  border: threat.risk_score >= 0.45 ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: '0.5rem'
                }}
              >
                <p
                  style={{
                    fontSize: '0.92rem',
                    color: threat.risk_score >= 0.45 ? '#fca5a5' : '#6ee7b7',
                    margin: 0,
                    fontWeight: 700,
                    lineHeight: 1.4
                  }}
                >
                  {threat.recommended_action || 'Monitoring active.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
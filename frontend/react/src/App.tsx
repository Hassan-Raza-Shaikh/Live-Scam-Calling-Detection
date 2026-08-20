import React, { useState, useEffect, useRef } from 'react';

interface ThreatData {
  risk_score: number;
  risk_level: string;
  fast_path_alert: boolean;
  latest_transcript: string;
  detected_tactics: string[];
  explanation: string;
  recommended_action: string;
  speaker?: string;
}

interface TranscriptItem {
  id: string;
  text: string;
  timestamp: string;
  speaker?: string;
  voiceMatchScore?: number;
  isScam?: boolean;
}

export default function App() {
  const [isLive, setIsLive] = useState(false);
  const [engine, setEngine] = useState<'webspeech' | 'scribe'>('webspeech');
  const [acousticMode, setAcousticMode] = useState<'mic' | 'recording'>('recording');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [liveInterim, setLiveInterim] = useState('');
  const [transcriptHistory, setTranscriptHistory] = useState<TranscriptItem[]>([]);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [micVolume, setMicVolume] = useState(0);

  // Voice Enrollment State
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [isEnrolling, setIsEnrolling] = useState(false);
  const [enrollmentStatus, setEnrollmentStatus] = useState<string | null>(null);
  const [speakerMode, setSpeakerMode] = useState<'AUTO' | 'OWNER' | 'CALLER'>('AUTO');
  const [micGain, setMicGain] = useState<number>(2.5);

  // File Upload State
  const [isUploading, setIsUploading] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<string | null>(null);

  const [threat, setThreat] = useState<ThreatData>({
    risk_score: 0.0,
    risk_level: 'LOW',
    fast_path_alert: false,
    latest_transcript: 'Call shield ready. Click "Start Live Call Shield" to begin listening.',
    detected_tactics: [],
    explanation: 'No suspicious activity detected yet.',
    recommended_action: 'Monitoring active. Speak normally into your microphone or play audio recording.'
  });

  const wsRef = useRef<WebSocket | null>(null);
  const isLiveRef = useRef(false);
  const recognitionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const silenceTimerRef = useRef<any>(null);
  const pendingInterimRef = useRef<string>('');
  const pcmBufferRef = useRef<Float32Array[]>([]);

  isLiveRef.current = isLive;

  // Check enrollment status on mount
  useEffect(() => {
    fetch(`http://${window.location.hostname}:8000/api/v1/voice/status`)
      .then((res) => res.json())
      .then((data) => {
        if (data.is_enrolled) setIsEnrolled(true);
      })
      .catch(() => {});
  }, []);

  const enrollUserVoice = async () => {
    try {
      setIsEnrolling(true);
      setEnrollmentStatus('Listening... Please speak for 3 seconds: "This is my voice registration for Sentinel AI"');

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      
      const audioChunks: Float32Array[] = [];
      processor.onaudioprocess = (e) => {
        audioChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      // Record for 3.5 seconds
      setTimeout(async () => {
        source.disconnect();
        processor.disconnect();
        stream.getTracks().forEach((track) => track.stop());
        await audioContext.close();

        // Flatten chunks
        let totalLength = 0;
        audioChunks.forEach((c) => (totalLength += c.length));
        const merged = new Float32Array(totalLength);
        let offset = 0;
        audioChunks.forEach((c) => {
          merged.set(c, offset);
          offset += c.length;
        });

        // Convert to int16 PCM
        const int16Buffer = float32ToInt16(merged);
        const base64Audio = bufferToBase64(int16Buffer);

        try {
          const res = await fetch(`http://${window.location.hostname}:8000/api/v1/voice/enroll`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio_base64: base64Audio, user_name: 'Owner' })
          });
          const data = await res.json();
          if (data.status === 'success') {
            setIsEnrolled(true);
            setSpeakerMode('AUTO');
            setEnrollmentStatus('✅ Voiceprint registered! Live speech will now automatically match against your voiceprint.');
            setTimeout(() => setEnrollmentStatus(null), 6000);
          } else {
            setEnrollmentStatus(`❌ Enrollment error: ${data.message}`);
          }
        } catch (err: any) {
          setEnrollmentStatus(`❌ Network error: ${err.message}`);
        } finally {
          setIsEnrolling(false);
        }
      }, 3500);
    } catch (err: any) {
      alert(`Could not access microphone: ${err.message}`);
      setIsEnrolling(false);
      setEnrollmentStatus(null);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      setUploadFeedback(`Analyzing "${file.name}"...`);

      const reader = new FileReader();
      reader.onload = async () => {
        const arrayBuffer = reader.result as ArrayBuffer;
        const base64Audio = bufferToBase64(arrayBuffer);

        try {
          const res = await fetch(`http://${window.location.hostname}:8000/api/v1/audio/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio_base64: base64Audio, filename: file.name })
          });
          const data = await res.json();
          if (data.status === 'success') {
            setThreat({
              risk_score: data.risk_score,
              risk_level: data.risk_level,
              fast_path_alert: data.fast_path_alert,
              latest_transcript: data.transcript,
              detected_tactics: data.detected_tactics || [],
              explanation: data.explanation || '',
              recommended_action: data.recommended_action || '',
              speaker: data.speaker
            });

            const newItem: TranscriptItem = {
              id: Math.random().toString(36).substring(2, 9),
              text: data.transcript,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              speaker: data.speaker,
              isScam: data.risk_score >= 0.45
            };
            setTranscriptHistory((prev) => [newItem, ...prev.slice(0, 19)]);
            setUploadFeedback(`✅ Analyzed "${file.name}" successfully!`);
          } else {
            setUploadFeedback(`❌ Analysis error: ${data.detail || 'Unknown error'}`);
          }
        } catch (err: any) {
          setUploadFeedback(`❌ Error analyzing file: ${err.message}`);
        } finally {
          setIsUploading(false);
        }
      };
      reader.readAsArrayBuffer(file);
    } catch (err: any) {
      setUploadFeedback(`❌ Error reading file: ${err.message}`);
      setIsUploading(false);
    }
  };

  const cleanup = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
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
    pcmBufferRef.current = [];
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

  const sendPhraseToBackend = (text: string, speakerOverride?: string) => {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();
    
    // Resolve target speaker (Owner in Green, Caller in Red)
    let targetSpeaker = speakerOverride;
    if (!targetSpeaker) {
      if (speakerMode === 'OWNER') targetSpeaker = 'OWNER';
      else if (speakerMode === 'CALLER') targetSpeaker = 'CALLER';
      else targetSpeaker = isEnrolled ? 'OWNER' : 'CALLER';
    }

    // Extract recent rolling PCM audio buffer for backend biometric acoustic verification
    let base64Audio = '';
    if (pcmBufferRef.current.length > 0) {
      let totalLen = 0;
      pcmBufferRef.current.forEach((c) => (totalLen += c.length));
      const merged = new Float32Array(totalLen);
      let offset = 0;
      pcmBufferRef.current.forEach((c) => {
        merged.set(c, offset);
        offset += c.length;
      });
      const int16Buf = float32ToInt16(merged);
      base64Audio = bufferToBase64(int16Buf);
    }

    // Clear any pending silence timer
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    pendingInterimRef.current = '';
    setLiveInterim('');

    // Append to local history immediately with initial speaker
    const newItem: TranscriptItem = {
      id: Math.random().toString(36).substring(2, 9),
      text: cleanText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      speaker: targetSpeaker
    };
    setTranscriptHistory((prev) => [newItem, ...prev.slice(0, 19)]);

    // Send to backend via WebSocket with audio chunk for acoustic verification
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          transcript: cleanText,
          audio_b64: base64Audio,
          speaker: speakerOverride || (speakerMode === 'AUTO' ? undefined : speakerMode)
        })
      );
    }
  };

  const startLiveSession = async () => {
    setIsLive(true);
    isLiveRef.current = true;
    pcmBufferRef.current = [];
    const newSessionId = `sess_${Math.random().toString(36).substring(2, 9)}`;
    setSessionId(newSessionId);

    const connectWebSocket = (targetSessionId: string) => {
      if (!isLiveRef.current) return;
      const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws/live/${targetSessionId}`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'threat_update') {
            setThreat(data);
            if (data.speaker) {
              setTranscriptHistory((prev) =>
                prev.map((item, idx) =>
                  idx === 0
                    ? {
                        ...item,
                        speaker: data.speaker,
                        voiceMatchScore: data.voice_match_score,
                        isScam: data.risk_score >= 0.45
                      }
                    : item
                )
              );
            }
          }
        } catch (err) {
          console.error('Error parsing backend message:', err);
        }
      };

      ws.onerror = (err) => {
        console.warn('WebSocket warning:', err);
      };

      ws.onclose = () => {
        console.log('WebSocket closed. Auto-reconnecting while shield is live...');
        if (isLiveRef.current) {
          setTimeout(() => {
            if (isLiveRef.current) {
              connectWebSocket(targetSessionId);
            }
          }, 600);
        }
      };
    };

    connectWebSocket(newSessionId);

    if (engine === 'webspeech') {
      // Path 1: Native Web Speech API
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

      if (!SpeechRecognition) {
        alert('Web Speech API is not supported in this browser. Please use Chrome or switch to Scribe v2 mode.');
        return;
      }

        const setupRecognition = () => {
          if (!isLiveRef.current) return;

          try {
            if (recognitionRef.current) {
              recognitionRef.current.onend = null;
              recognitionRef.current.onerror = null;
              try {
                recognitionRef.current.stop();
              } catch (e) {}
              recognitionRef.current = null;
            }
          } catch (e) {}

          const SpeechRecognition =
            (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'en-US';
          recognition.maxAlternatives = 1;

          recognition.onstart = () => {
            if (isLiveRef.current) {
              setIsRecognizing(true);
            }
          };

          recognition.onresult = (event: any) => {
            let fullInterim = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
              const piece = event.results[i][0].transcript;
              if (event.results[i].isFinal) {
                if (piece && piece.trim()) {
                  sendPhraseToBackend(piece);
                  fullInterim = '';
                  setLiveInterim('');
                  pendingInterimRef.current = '';
                }
              } else {
                fullInterim += piece;
              }
            }

            if (fullInterim) {
              setLiveInterim(fullInterim);
              pendingInterimRef.current = fullInterim;
            }
          };

          recognition.onerror = (event: any) => {
            console.log('Speech recognition event:', event.error);
            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
              alert('Microphone access was denied. Please allow microphone access in your browser settings.');
              stopLiveSession();
              return;
            }
            // For no-speech or network or aborted, let onend handle restart
          };

          recognition.onend = () => {
            setIsRecognizing(false);
            // If user stopped live shield intentionally, do nothing
            if (!isLiveRef.current) return;

            // Chrome closes recognition after long pauses or sentence completions.
            // Restart seamlessly after a 200ms cooldown so mic never permanently closes!
            setTimeout(() => {
              if (isLiveRef.current) {
                setupRecognition();
              }
            }, 200);
          };

          try {
            recognition.start();
            recognitionRef.current = recognition;
          } catch (err: any) {
            console.warn('Recognition start exception:', err);
            if (isLiveRef.current) {
              setTimeout(() => {
                if (isLiveRef.current) setupRecognition();
              }, 300);
            }
          }
        };

        setupRecognition();

        // Audio processor & visualizer
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          streamRef.current = stream;
          const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
          audioContextRef.current = audioCtx;

          const source = audioCtx.createMediaStreamSource(stream);
          const boostNode = audioCtx.createGain();
          boostNode.gain.value = micGain;

          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 256;

          const processor = audioCtx.createScriptProcessor(4096, 1, 1);

          source.connect(boostNode);
          boostNode.connect(analyser);
          boostNode.connect(processor);

          const gainMute = audioCtx.createGain();
          gainMute.gain.value = 0;
          processor.connect(gainMute);
          gainMute.connect(audioCtx.destination);

          processor.onaudioprocess = (e) => {
            if (!isLiveRef.current) return;
            const data = e.inputBuffer.getChannelData(0);
            pcmBufferRef.current.push(new Float32Array(data));
            if (pcmBufferRef.current.length > 14) {
              pcmBufferRef.current.shift();
            }
          };

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
          console.warn('Audio capture setup warning:', e);
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
            if (!isLiveRef.current) return;
            const inputData = e.inputBuffer.getChannelData(0);
            const int16Buffer = float32ToInt16(inputData);
            const base64Audio = bufferToBase64(int16Buffer);

            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ audio_b64: base64Audio }));
            }
          };
        } catch (err: any) {
          console.error('Microphone stream error:', err);
          alert('Could not access microphone. Please check permissions.');
      }
    }
  };

  const stopLiveSession = () => {
    setIsLive(false);
    isLiveRef.current = false;
    cleanup();
  };

  useEffect(() => {
    return () => {
      cleanup();
    };
  }, []);

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#030712', color: '#f3f4f6', fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', padding: '1.5rem 2rem' }}>
      {/* Top Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <span style={{ fontSize: '1.6rem' }}>🛡️</span>
            <h1 style={{ fontSize: '1.45rem', fontWeight: 800, margin: 0, background: 'linear-gradient(90deg, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Sentinel AI
            </h1>
            <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', borderRadius: '1rem', backgroundColor: '#1e293b', color: '#94a3b8', border: '1px solid #334155' }}>
              Live Anti-Scam Shield v2.4
            </span>
          </div>
          <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.82rem', color: '#64748b' }}>
            Real-time biometric speaker verification, deep social engineering analysis & fast-path threat defense
          </p>
        </div>

        {/* Global Action Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Engine Selector */}
          <div style={{ display: 'flex', backgroundColor: '#0f172a', padding: '0.25rem', borderRadius: '0.5rem', border: '1px solid #1e293b' }}>
            <button
              onClick={() => setEngine('webspeech')}
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: '0.35rem',
                border: 'none',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: engine === 'webspeech' ? '#2563eb' : 'transparent',
                color: engine === 'webspeech' ? '#ffffff' : '#9ca3af',
                transition: 'all 0.2s ease'
              }}
            >
              Web Speech (Instant Local)
            </button>
            <button
              onClick={() => setEngine('scribe')}
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: '0.35rem',
                border: 'none',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: engine === 'scribe' ? '#2563eb' : 'transparent',
                color: engine === 'scribe' ? '#ffffff' : '#9ca3af',
                transition: 'all 0.2s ease'
              }}
            >
              Scribe v2 (Cloud Neural)
            </button>
          </div>

          {/* Master Live Toggle Button */}
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

      {/* Voice Enrollment & Audio Testing Toolbar */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
        {/* Card 1: Voiceprint Registration & Attribution Mode */}
        <div style={{ padding: '0.85rem 1.15rem', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f3f4f6' }}>👤 Multi-Biometric Voiceprint (MFCC + Pitch F0)</span>
                <span style={{ fontSize: '0.75rem', padding: '0.15rem 0.5rem', borderRadius: '1rem', backgroundColor: isEnrolled ? 'rgba(16, 185, 129, 0.2)' : 'rgba(107, 114, 128, 0.2)', border: isEnrolled ? '1px solid #10b981' : '1px solid #6b7280', color: isEnrolled ? '#6ee7b7' : '#9ca3af', fontWeight: 600 }}>
                  {isEnrolled ? '✅ Enrolled (Owner Active)' : '⚪ Not Enrolled'}
                </span>
              </div>
              <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.75rem', color: '#9ca3af' }}>
                Register your voice. Incoming audio is matched against your vocal tract MFCCs and pitch.
              </p>
            </div>

            <button
              onClick={enrollUserVoice}
              disabled={isEnrolling}
              style={{
                padding: '0.45rem 0.8rem',
                borderRadius: '0.5rem',
                backgroundColor: isEnrolling ? '#d97706' : '#2563eb',
                color: '#ffffff',
                border: 'none',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: isEnrolling ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                boxShadow: '0 0 10px rgba(37, 99, 235, 0.3)'
              }}
            >
              {isEnrolling ? '⏳ Recording (3s)...' : '🎙️ Register My Voice'}
            </button>
          </div>

          {/* Speaker Mode Toggle Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', backgroundColor: '#030712', padding: '0.35rem', borderRadius: '0.5rem', border: '1px solid #1e293b' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 600, marginLeft: '0.3rem' }}>MODE:</span>
            <button
              onClick={() => setSpeakerMode('AUTO')}
              style={{
                flex: 1,
                padding: '0.35rem 0.5rem',
                borderRadius: '0.35rem',
                border: 'none',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                backgroundColor: speakerMode === 'AUTO' ? '#3b82f6' : 'transparent',
                color: speakerMode === 'AUTO' ? '#ffffff' : '#9ca3af',
                transition: 'all 0.15s ease'
              }}
            >
              🎯 Auto Biometric (Recommended)
            </button>
            <button
              onClick={() => setSpeakerMode('OWNER')}
              style={{
                flex: 1,
                padding: '0.35rem 0.5rem',
                borderRadius: '0.35rem',
                border: 'none',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                backgroundColor: speakerMode === 'OWNER' ? '#10b981' : 'transparent',
                color: speakerMode === 'OWNER' ? '#ffffff' : '#9ca3af',
                transition: 'all 0.15s ease'
              }}
            >
              🟢 Lock YOU (Owner)
            </button>
            <button
              onClick={() => setSpeakerMode('CALLER')}
              style={{
                flex: 1,
                padding: '0.35rem 0.5rem',
                borderRadius: '0.35rem',
                border: 'none',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                backgroundColor: speakerMode === 'CALLER' ? '#ef4444' : 'transparent',
                color: speakerMode === 'CALLER' ? '#ffffff' : '#9ca3af',
                transition: 'all 0.15s ease'
              }}
            >
              🔴 Lock CALLER (Scammer)
            </button>
          </div>
        </div>

        {/* Card 2: Mic Sensitivity Booster & Audio File Testing */}
        <div style={{ padding: '0.85rem 1.15rem', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f3f4f6' }}>📁 Audio File & Phone Recording Test</span>
              </div>
              <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.75rem', color: '#9ca3af' }}>
                Upload .wav/.mp3 calls directly or boost mic sensitivity for distant audio.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <label
                style={{
                  padding: '0.45rem 0.8rem',
                  borderRadius: '0.5rem',
                  backgroundColor: '#4f46e5',
                  color: '#ffffff',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  cursor: isUploading ? 'not-allowed' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  boxShadow: '0 0 10px rgba(79, 70, 229, 0.3)'
                }}
              >
                {isUploading ? '⏳ Analyzing...' : '📤 Upload Audio File'}
                <input
                  type="file"
                  accept="audio/*,.wav,.mp3,.m4a"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  style={{ display: 'none' }}
                />
              </label>
            </div>
          </div>

          {/* Mic Gain Boost Slider Bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', backgroundColor: '#030712', padding: '0.35rem 0.75rem', borderRadius: '0.5rem', border: '1px solid #1e293b' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 600, whiteSpace: 'nowrap' }}>
              🔊 MIC SENSITIVITY BOOST: {micGain.toFixed(1)}x
            </span>
            <input
              type="range"
              min="1.0"
              max="5.0"
              step="0.5"
              value={micGain}
              onChange={(e) => setMicGain(parseFloat(e.target.value))}
              style={{ flex: 1, accentColor: '#38bdf8', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>
              {micGain >= 3.0 ? '⚡ High (Phone Speakers)' : 'Normal'}
            </span>
          </div>
        </div>
      </div>

      {/* Enrollment / Upload Status Notification */}
      {(enrollmentStatus || uploadFeedback) && (
        <div style={{ padding: '0.65rem 1rem', borderRadius: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', color: '#38bdf8', fontSize: '0.82rem', marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{enrollmentStatus || uploadFeedback}</span>
          <button onClick={() => { setEnrollmentStatus(null); setUploadFeedback(null); }} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '0.9rem' }}>✕</button>
        </div>
      )}

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
              <p style={{ margin: 0, fontSize: '0.75rem', color: '#9ca3af' }}>Speak into your mic or play audio recording to test real-time detection</p>
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
                  transition: 'width 0.3s ease'
                }}
              />
            </div>
          </div>

          {/* Live Transcript Display */}
          <div style={{ padding: '1.25rem', borderRadius: '0.85rem', backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '0.875rem', color: '#38bdf8', margin: 0, fontWeight: 600 }}>
                  💬 Live Multi-Speaker Transcript Stream
                </h3>
                {threat.speaker && (
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      padding: '0.15rem 0.5rem',
                      borderRadius: '1rem',
                      backgroundColor: threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                      border: threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? '1px solid #10b981' : '1px solid #ef4444',
                      color: threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? '#6ee7b7' : '#fca5a5'
                    }}
                  >
                    {threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? '🟢 YOU (Owner)' : '🔴 CALLER (Suspected Scammer)'}
                  </span>
                )}
              </div>
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
                backgroundColor: threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
                borderRadius: '0.5rem',
                border: threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
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
                  {isLive ? 'Listening... say something into your mic or play audio!' : 'Shield is stopped. Click Start above.'}
                </span>
              )}
            </div>

            {/* Transcript Log History with Green / Red Speaker Cards & Voice Match Badge */}
            {transcriptHistory.length > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <h4 style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', margin: '0 0 0.5rem 0', letterSpacing: '0.05em' }}>
                  Conversation Timeline (🟢 Owner in Green | 🔴 Caller in Red)
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '200px', overflowY: 'auto' }}>
                  {transcriptHistory.map((item) => {
                    const isOwner = item.speaker === 'OWNER' || item.speaker === 'VICTIM' || item.speaker === 'USER';
                    return (
                      <div
                        key={item.id}
                        style={{
                          fontSize: '0.82rem',
                          padding: '0.5rem 0.75rem',
                          borderRadius: '0.45rem',
                          backgroundColor: isOwner ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                          borderLeft: isOwner ? '4px solid #10b981' : '4px solid #ef4444',
                          border: isOwner ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(239, 68, 68, 0.25)',
                          color: '#f3f4f6',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.25rem'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: 700, fontSize: '0.75rem', color: isOwner ? '#34d399' : '#f87171' }}>
                              {isOwner ? '🟢 [OWNER / YOU]' : '🔴 [CALLER / SCAMMER]'}
                            </span>
                            {item.voiceMatchScore !== undefined && item.voiceMatchScore > 0 && (
                              <span
                                style={{
                                  fontSize: '0.68rem',
                                  padding: '0.1rem 0.4rem',
                                  borderRadius: '0.25rem',
                                  backgroundColor: item.voiceMatchScore >= 75 ? 'rgba(52, 211, 153, 0.2)' : 'rgba(248, 113, 113, 0.2)',
                                  color: item.voiceMatchScore >= 75 ? '#34d399' : '#f87171',
                                  fontWeight: 600
                                }}
                              >
                                {item.voiceMatchScore}% Biometric Match
                              </span>
                            )}
                          </div>
                          <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>{item.timestamp}</span>
                        </div>
                        <div style={{ fontSize: '0.88rem', color: isOwner ? '#e6fffa' : '#ffe4e6' }}>
                          "{item.text}"
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Speaker Selection & 2-Speaker Interactive Simulation */}
          <div style={{ padding: '1.25rem', borderRadius: '0.85rem', backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h3 style={{ fontSize: '0.85rem', color: '#9ca3af', margin: 0, fontWeight: 600 }}>
                👥 Active Speaker Toggle & 2-Speaker Scam Call Demo
              </h3>
              
              {/* Speaker Toggle Buttons */}
              <div style={{ display: 'flex', gap: '0.35rem' }}>
                <button
                  onClick={() => setSpeakerMode('CALLER')}
                  style={{
                    padding: '0.3rem 0.6rem',
                    borderRadius: '0.35rem',
                    border: 'none',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    backgroundColor: speakerMode === 'CALLER' ? '#ef4444' : '#1e293b',
                    color: '#ffffff'
                  }}
                >
                  🔴 Caller (Scammer)
                </button>
                <button
                  onClick={() => setSpeakerMode('OWNER')}
                  style={{
                    padding: '0.3rem 0.6rem',
                    borderRadius: '0.35rem',
                    border: 'none',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    backgroundColor: speakerMode === 'OWNER' ? '#10b981' : '#1e293b',
                    color: '#ffffff'
                  }}
                >
                  🟢 You (Owner)
                </button>
              </div>
            </div>

            {/* 2-Speaker Dialogue Preset Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <button
                onClick={() => sendPhraseToBackend('This is Chase Bank Fraud Department. Unauthorized transaction of $2,500 detected on your account.', 'CALLER')}
                disabled={!isLive}
                style={{ padding: '0.6rem 0.8rem', backgroundColor: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '0.5rem', color: '#fca5a5', fontSize: '0.78rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5, fontWeight: 600 }}
              >
                🔴 Caller: "Unauthorized $2,500"
              </button>
              <button
                onClick={() => sendPhraseToBackend('Wait, what unauthorized transaction? Why is my card blocked?', 'OWNER')}
                disabled={!isLive}
                style={{ padding: '0.6rem 0.8rem', backgroundColor: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', borderRadius: '0.5rem', color: '#6ee7b7', fontSize: '0.78rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5, fontWeight: 600 }}
              >
                🟢 You: "Why is card blocked?"
              </button>
              <button
                onClick={() => sendPhraseToBackend('To cancel the charge right now, read me the 6-digit verification code sent to your phone immediately.', 'CALLER')}
                disabled={!isLive}
                style={{ padding: '0.6rem 0.8rem', backgroundColor: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '0.5rem', color: '#fca5a5', fontSize: '0.78rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5, fontWeight: 600 }}
              >
                🔴 Caller: "Read me 6-digit OTP"
              </button>
              <button
                onClick={() => sendPhraseToBackend('My SMS says never share this code with anyone. Who is your supervisor?', 'OWNER')}
                disabled={!isLive}
                style={{ padding: '0.6rem 0.8rem', backgroundColor: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', borderRadius: '0.5rem', color: '#6ee7b7', fontSize: '0.78rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5, fontWeight: 600 }}
              >
                🟢 You: "SMS says never share code"
              </button>
            </div>

            {/* Custom Text Input */}
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                id="testInputOverride"
                placeholder={speakerMode === 'CALLER' ? "Type phrase as 🔴 CALLER (Scammer)..." : "Type phrase as 🟢 YOU (Owner)..."}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const input = e.currentTarget;
                    if (input && input.value.trim()) {
                      sendPhraseToBackend(input.value, speakerMode === 'AUTO' ? undefined : speakerMode);
                      input.value = '';
                    }
                  }
                }}
                style={{ flex: 1, padding: '0.6rem 0.8rem', borderRadius: '0.5rem', border: speakerMode === 'CALLER' ? '1px solid #ef4444' : '1px solid #10b981', backgroundColor: '#030712', color: 'white', fontSize: '0.85rem' }}
              />
              <button
                onClick={() => {
                  const input = document.getElementById('testInputOverride') as HTMLInputElement;
                  if (input && input.value.trim()) {
                    sendPhraseToBackend(input.value, speakerMode === 'AUTO' ? undefined : speakerMode);
                    input.value = '';
                  }
                }}
                disabled={!isLive}
                style={{
                  padding: '0.6rem 1rem',
                  backgroundColor: speakerMode === 'CALLER' ? '#ef4444' : '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: isLive ? 'pointer' : 'not-allowed',
                  opacity: isLive ? 1 : 0.5
                }}
              >
                Send as {speakerMode === 'CALLER' ? 'Caller' : 'You'}
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
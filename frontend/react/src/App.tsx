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
    <div style={{ minHeight: '100vh', backgroundColor: '#090d16', color: '#f1f5f9', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif', padding: '1.5rem 2rem' }}>
      {/* Top Header Bar */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', borderBottom: '1px solid #1e293b', paddingBottom: '1.1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '8px', backgroundColor: '#1e293b', border: '1px solid #334155', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <h1 style={{ fontSize: '1.35rem', fontWeight: 700, margin: 0, color: '#f8fafc', letterSpacing: '-0.02em' }}>
                Sentinel Security
              </h1>
              <span style={{ fontSize: '0.72rem', padding: '0.15rem 0.55rem', borderRadius: '4px', backgroundColor: '#1e293b', color: '#94a3b8', border: '1px solid #334155', fontWeight: 600 }}>
                Live Call Monitor
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.72rem', color: isLive ? '#34d399' : '#94a3b8' }}>
                <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: isLive ? '#10b981' : '#64748b', display: 'inline-block' }} />
                {isLive ? 'Active Session' : 'Idle'}
              </span>
            </div>
            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.8rem', color: '#64748b' }}>
              Real-time voice biometric verification, fraud taxonomy classification, and call defense
            </p>
          </div>
        </div>

        {/* Global Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Engine Selector */}
          <div style={{ display: 'flex', backgroundColor: '#0f172a', padding: '0.2rem', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <button
              onClick={() => setEngine('webspeech')}
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: '4px',
                border: 'none',
                fontSize: '0.76rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: engine === 'webspeech' ? '#2563eb' : 'transparent',
                color: engine === 'webspeech' ? '#ffffff' : '#94a3b8',
                transition: 'background 0.15s ease'
              }}
            >
              Web Speech
            </button>
            <button
              onClick={() => setEngine('scribe')}
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: '4px',
                border: 'none',
                fontSize: '0.76rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: engine === 'scribe' ? '#2563eb' : 'transparent',
                color: engine === 'scribe' ? '#ffffff' : '#94a3b8',
                transition: 'background 0.15s ease'
              }}
            >
              Scribe v2
            </button>
          </div>

          {/* Master Live Toggle */}
          <button
            onClick={isLive ? stopLiveSession : startLiveSession}
            style={{
              padding: '0.55rem 1.25rem',
              borderRadius: '6px',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              fontSize: '0.88rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              backgroundColor: isLive ? '#dc2626' : '#059669',
              color: '#ffffff',
              transition: 'background 0.15s ease'
            }}
          >
            {isLive ? (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="6" width="12" height="12" rx="2"/>
                </svg>
                Stop Monitoring
              </>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" y1="19" x2="12" y2="23"/>
                  <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
                Start Live Monitoring
              </>
            )}
          </button>
        </div>
      </header>

      {/* Voice Verification & Audio Configuration Section */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
        {/* Card 1: Voice Authentication */}
        <div style={{ padding: '1rem 1.2rem', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: 600, color: '#f1f5f9' }}>Voice Authentication Profile</span>
                <span style={{ fontSize: '0.72rem', padding: '0.15rem 0.5rem', borderRadius: '4px', backgroundColor: isEnrolled ? 'rgba(16, 185, 129, 0.15)' : '#1e293b', border: isEnrolled ? '1px solid #059669' : '1px solid #334155', color: isEnrolled ? '#34d399' : '#94a3b8', fontWeight: 600 }}>
                  {isEnrolled ? 'Registered (Owner Active)' : 'Unregistered'}
                </span>
              </div>
              <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.76rem', color: '#64748b' }}>
                Audio is matched against your vocal tract MFCC profile and fundamental frequency.
              </p>
            </div>

            <button
              onClick={enrollUserVoice}
              disabled={isEnrolling}
              style={{
                padding: '0.4rem 0.8rem',
                borderRadius: '6px',
                backgroundColor: isEnrolling ? '#d97706' : '#1e293b',
                color: '#f8fafc',
                border: '1px solid #334155',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: isEnrolling ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem'
              }}
            >
              {isEnrolling ? 'Recording Sample (3s)...' : 'Record Voice Sample'}
            </button>
          </div>

          {/* Speaker Attribution Mode */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', backgroundColor: '#020617', padding: '0.3rem', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <span style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 600, marginLeft: '0.35rem' }}>SPEAKER:</span>
            <button
              onClick={() => setSpeakerMode('AUTO')}
              style={{
                flex: 1,
                padding: '0.35rem 0.5rem',
                borderRadius: '4px',
                border: 'none',
                fontSize: '0.74rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: speakerMode === 'AUTO' ? '#2563eb' : 'transparent',
                color: speakerMode === 'AUTO' ? '#ffffff' : '#94a3b8'
              }}
            >
              Auto Biometrics
            </button>
            <button
              onClick={() => setSpeakerMode('OWNER')}
              style={{
                flex: 1,
                padding: '0.35rem 0.5rem',
                borderRadius: '4px',
                border: 'none',
                fontSize: '0.74rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: speakerMode === 'OWNER' ? '#059669' : 'transparent',
                color: speakerMode === 'OWNER' ? '#ffffff' : '#94a3b8'
              }}
            >
              Force User (You)
            </button>
            <button
              onClick={() => setSpeakerMode('CALLER')}
              style={{
                flex: 1,
                padding: '0.35rem 0.5rem',
                borderRadius: '4px',
                border: 'none',
                fontSize: '0.74rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: speakerMode === 'CALLER' ? '#dc2626' : 'transparent',
                color: speakerMode === 'CALLER' ? '#ffffff' : '#94a3b8'
              }}
            >
              Force Caller
            </button>
          </div>
        </div>

        {/* Card 2: Audio File Analysis & Gain Control */}
        <div style={{ padding: '1rem 1.2rem', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <span style={{ fontSize: '0.88rem', fontWeight: 600, color: '#f1f5f9' }}>Audio Recording Analysis</span>
              <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.76rem', color: '#64748b' }}>
                Upload .wav or .mp3 call recordings or adjust input gain for quiet microphones.
              </p>
            </div>

            <label
              style={{
                padding: '0.4rem 0.8rem',
                borderRadius: '6px',
                backgroundColor: '#1e293b',
                color: '#f8fafc',
                border: '1px solid #334155',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: isUploading ? 'not-allowed' : 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem'
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              {isUploading ? 'Analyzing...' : 'Upload Call File'}
              <input
                type="file"
                accept="audio/*,.wav,.mp3,.m4a"
                onChange={handleFileUpload}
                disabled={isUploading}
                style={{ display: 'none' }}
              />
            </label>
          </div>

          {/* Gain Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', backgroundColor: '#020617', padding: '0.35rem 0.75rem', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 600, whiteSpace: 'nowrap' }}>
              INPUT GAIN: {micGain.toFixed(1)}x
            </span>
            <input
              type="range"
              min="1.0"
              max="5.0"
              step="0.5"
              value={micGain}
              onChange={(e) => setMicGain(parseFloat(e.target.value))}
              style={{ flex: 1, accentColor: '#2563eb', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
              {micGain >= 3.0 ? 'Boosted (Phone Speakers)' : 'Standard'}
            </span>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {(enrollmentStatus || uploadFeedback) && (
        <div style={{ padding: '0.65rem 1rem', borderRadius: '6px', backgroundColor: '#0f172a', border: '1px solid #334155', color: '#38bdf8', fontSize: '0.8rem', marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{enrollmentStatus || uploadFeedback}</span>
          <button onClick={() => { setEnrollmentStatus(null); setUploadFeedback(null); }} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '0.85rem' }}>✕</button>
        </div>
      )}

      {/* Live Active Bar */}
      {isLive && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.7rem 1.25rem', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: isRecognizing ? '#10b981' : '#f59e0b', display: 'inline-block' }} />
            <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc' }}>
              {isRecognizing ? 'Microphone Active — Listening to Live Stream' : 'Connecting Audio Stream...'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '150px' }}>
            <span style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Volume</span>
            <div style={{ flex: 1, height: '6px', backgroundColor: '#1e293b', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{ width: `${micVolume}%`, height: '100%', backgroundColor: micVolume > 60 ? '#ef4444' : '#10b981', transition: 'width 0.1s ease' }} />
            </div>
          </div>
        </div>
      )}

      {/* Main Analysis Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '1.5rem' }}>
        {/* Left Column: Live Transcript & Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Threat Meter Bar */}
          <div style={{ padding: '1.1rem 1.25rem', borderRadius: '8px', backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.82rem', color: '#94a3b8', fontWeight: 600 }}>Threat Level Assessment</span>
              <span style={{ fontWeight: 700, fontSize: '0.95rem', color: threat.risk_score > 0.7 ? '#f43f5e' : threat.risk_score > 0.4 ? '#fbbf24' : '#34d399' }}>
                {(threat.risk_score * 100).toFixed(0)}% [{threat.risk_level}]
              </span>
            </div>
            <div style={{ width: '100%', height: '8px', backgroundColor: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${threat.risk_score * 100}%`,
                  height: '100%',
                  backgroundColor: threat.risk_score > 0.7 ? '#f43f5e' : threat.risk_score > 0.4 ? '#fbbf24' : '#10b981',
                  transition: 'width 0.3s ease'
                }}
              />
            </div>
          </div>

          {/* Active Transcription */}
          <div style={{ padding: '1.25rem', borderRadius: '8px', backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', color: '#f8fafc', fontWeight: 600 }}>Live Dialogue Stream</span>
                {threat.speaker && (
                  <span
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '0.15rem 0.5rem',
                      borderRadius: '4px',
                      backgroundColor: threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      border: threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? '1px solid #059669' : '1px solid #dc2626',
                      color: threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? '#34d399' : '#f87171'
                    }}
                  >
                    {threat.speaker === 'OWNER' || threat.speaker === 'VICTIM' || threat.speaker === 'USER' ? 'User (You)' : 'Incoming Caller'}
                  </span>
                )}
              </div>
              {liveInterim && (
                <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                  Processing audio...
                </span>
              )}
            </div>

            <div
              style={{
                padding: '0.85rem 1rem',
                backgroundColor: '#020617',
                borderRadius: '6px',
                border: '1px solid #1e293b',
                minHeight: '65px',
                fontSize: '0.88rem',
                color: '#e2e8f0',
                lineHeight: 1.5,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center'
              }}
            >
              {liveInterim ? (
                <span style={{ color: '#93c5fd' }}>"{liveInterim}"</span>
              ) : transcriptHistory.length > 0 ? (
                <span>"{transcriptHistory[0].text}"</span>
              ) : (
                <span style={{ color: '#475569' }}>
                  {isLive ? 'Listening for speech...' : 'Monitoring paused. Click Start above to begin.'}
                </span>
              )}
            </div>

            {/* Conversation Log */}
            {transcriptHistory.length > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                  Turn History
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', maxHeight: '220px', overflowY: 'auto' }}>
                  {transcriptHistory.map((item) => {
                    const isOwner = item.speaker === 'OWNER' || item.speaker === 'VICTIM' || item.speaker === 'USER';
                    return (
                      <div
                        key={item.id}
                        style={{
                          fontSize: '0.82rem',
                          padding: '0.55rem 0.75rem',
                          borderRadius: '6px',
                          backgroundColor: isOwner ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
                          borderLeft: isOwner ? '3px solid #10b981' : '3px solid #ef4444',
                          border: isOwner ? '1px solid rgba(16, 185, 129, 0.2)' : '1px solid rgba(239, 68, 68, 0.2)',
                          color: '#f8fafc',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.2rem'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <span style={{ fontWeight: 600, fontSize: '0.74rem', color: isOwner ? '#34d399' : '#f87171' }}>
                              {isOwner ? 'User (You)' : 'Caller'}
                            </span>
                            {item.voiceMatchScore !== undefined && item.voiceMatchScore > 0 && (
                              <span
                                style={{
                                  fontSize: '0.66rem',
                                  padding: '0.05rem 0.35rem',
                                  borderRadius: '3px',
                                  backgroundColor: '#1e293b',
                                  color: '#94a3b8'
                                }}
                              >
                                {item.voiceMatchScore}% Match
                              </span>
                            )}
                          </div>
                          <span style={{ fontSize: '0.68rem', color: '#64748b' }}>{item.timestamp}</span>
                        </div>
                        <div style={{ fontSize: '0.84rem', color: '#e2e8f0' }}>
                          "{item.text}"
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Test Scenarios Panel */}
          <div style={{ padding: '1.1rem 1.25rem', borderRadius: '8px', backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
              <span style={{ fontSize: '0.82rem', color: '#94a3b8', fontWeight: 600 }}>
                Simulate Dialogue Turns
              </span>
              <div style={{ display: 'flex', gap: '0.35rem' }}>
                <button
                  onClick={() => setSpeakerMode('CALLER')}
                  style={{
                    padding: '0.25rem 0.55rem',
                    borderRadius: '4px',
                    border: 'none',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    backgroundColor: speakerMode === 'CALLER' ? '#dc2626' : '#1e293b',
                    color: '#ffffff'
                  }}
                >
                  Caller
                </button>
                <button
                  onClick={() => setSpeakerMode('OWNER')}
                  style={{
                    padding: '0.25rem 0.55rem',
                    borderRadius: '4px',
                    border: 'none',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    backgroundColor: speakerMode === 'OWNER' ? '#059669' : '#1e293b',
                    color: '#ffffff'
                  }}
                >
                  You
                </button>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.45rem', marginBottom: '0.65rem' }}>
              <button
                onClick={() => sendPhraseToBackend('This is Chase Bank Fraud Department. Unauthorized transaction of $2,500 detected on your account.', 'CALLER')}
                disabled={!isLive}
                style={{ padding: '0.5rem 0.7rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', fontSize: '0.76rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5 }}
              >
                Caller: "Unauthorized $2,500"
              </button>
              <button
                onClick={() => sendPhraseToBackend('Wait, what unauthorized transaction? Why is my card blocked?', 'OWNER')}
                disabled={!isLive}
                style={{ padding: '0.5rem 0.7rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', fontSize: '0.76rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5 }}
              >
                You: "Why is card blocked?"
              </button>
              <button
                onClick={() => sendPhraseToBackend('To cancel the charge right now, read me the 6-digit verification code sent to your phone immediately.', 'CALLER')}
                disabled={!isLive}
                style={{ padding: '0.5rem 0.7rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', fontSize: '0.76rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5 }}
              >
                Caller: "Read me 6-digit OTP"
              </button>
              <button
                onClick={() => sendPhraseToBackend('My SMS says never share this code with anyone. Who is your supervisor?', 'OWNER')}
                disabled={!isLive}
                style={{ padding: '0.5rem 0.7rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', fontSize: '0.76rem', textAlign: 'left', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.5 }}
              >
                You: "SMS says never share code"
              </button>
            </div>

            {/* Custom Input */}
            <div style={{ display: 'flex', gap: '0.45rem' }}>
              <input
                id="testInputOverride"
                placeholder={speakerMode === 'CALLER' ? "Type test sentence as Caller..." : "Type test sentence as User..."}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const input = e.currentTarget;
                    if (input && input.value.trim()) {
                      sendPhraseToBackend(input.value, speakerMode === 'AUTO' ? undefined : speakerMode);
                      input.value = '';
                    }
                  }
                }}
                style={{ flex: 1, padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid #334155', backgroundColor: '#020617', color: '#f8fafc', fontSize: '0.82rem' }}
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
                  padding: '0.5rem 0.85rem',
                  backgroundColor: '#1e293b',
                  color: '#f8fafc',
                  border: '1px solid #334155',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  cursor: isLive ? 'pointer' : 'not-allowed',
                  opacity: isLive ? 1 : 0.5
                }}
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Threat Analysis & Recommendations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Fast-Path Alert Banner */}
          {threat.fast_path_alert && (
            <div
              style={{
                padding: '1rem 1.25rem',
                borderRadius: '8px',
                backgroundColor: '#450a0a',
                border: '1px solid #dc2626',
                color: '#fee2e2'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.95rem', color: '#fca5a5', marginBottom: '0.25rem' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                CRITICAL THREAT: Fast-Path Credential Interception
              </div>
              <div style={{ fontSize: '0.82rem', color: '#fecaca' }}>
                Unauthorized verification code or credential demand intercepted. Refuse immediately.
              </div>
            </div>
          )}

          {/* Analysis Card */}
          <div style={{ padding: '1.25rem', borderRadius: '8px', backgroundColor: '#0f172a', border: '1px solid #1e293b', flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.01em' }}>
                Security Analysis & Threat Intelligence
              </span>
              <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.76rem', color: '#64748b' }}>
                Multi-agent heuristic evaluation across 26 fraud taxonomies
              </p>
            </div>

            <div>
              <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: '0.45rem', fontWeight: 600 }}>
                Detected Fraud Indicators
              </span>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                {threat.detected_tactics && threat.detected_tactics.length > 0 ? (
                  threat.detected_tactics.map((tactic, idx) => (
                    <span
                      key={idx}
                      style={{
                        padding: '0.25rem 0.65rem',
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '4px',
                        fontSize: '0.76rem',
                        fontWeight: 600,
                        color: '#f87171'
                      }}
                    >
                      {tactic}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>No threat indicators identified</span>
                )}
              </div>
            </div>

            <div>
              <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: '0.45rem', fontWeight: 600 }}>
                Evidence & Findings
              </span>
              <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: 1.5, backgroundColor: '#020617', padding: '0.75rem 0.9rem', borderRadius: '6px', border: '1px solid #1e293b', margin: 0 }}>
                {threat.explanation || 'Monitoring conversation stream for deceptive patterns...'}
              </p>
            </div>

            <div style={{ marginTop: 'auto' }}>
              <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: '0.45rem', fontWeight: 600 }}>
                Recommended Action
              </span>
              <div
                style={{
                  padding: '0.75rem 0.95rem',
                  backgroundColor: threat.risk_score >= 0.45 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.08)',
                  border: threat.risk_score >= 0.45 ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(16, 185, 129, 0.25)',
                  borderRadius: '6px'
                }}
              >
                <p
                  style={{
                    fontSize: '0.86rem',
                    color: threat.risk_score >= 0.45 ? '#fca5a5' : '#6ee7b7',
                    margin: 0,
                    fontWeight: 600,
                    lineHeight: 1.45
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
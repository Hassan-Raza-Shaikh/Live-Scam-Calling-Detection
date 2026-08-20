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
  const [speakerGapDelayMs, setSpeakerGapDelayMs] = useState<number>(450);

  // File Upload State
  const [isUploading, setIsUploading] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<string | null>(null);
  const [audioAlertsEnabled, setAudioAlertsEnabled] = useState(true);

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
  const prevThreatPercentRef = useRef<number>(0);
  const audioAlertsEnabledRef = useRef<boolean>(true);
  const speakerGapDelayMsRef = useRef<number>(450);
  audioAlertsEnabledRef.current = audioAlertsEnabled;
  speakerGapDelayMsRef.current = speakerGapDelayMs;

  const playSubtleWarningChime = (threatPercent: number) => {
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioContextClass) return;
      const ctx = new AudioContextClass();

      const gainNode = ctx.createGain();
      gainNode.gain.setValueAtTime(0.0001, ctx.currentTime);
      gainNode.gain.linearRampToValueAtTime(0.12, ctx.currentTime + 0.02);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.35);
      gainNode.connect(ctx.destination);

      // Warm subtle dual-tone sine wave chime (scales smoothly with severity)
      const baseFreq = 540 + Math.min(240, (threatPercent - 50) * 4);
      const osc1 = ctx.createOscillator();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(baseFreq, ctx.currentTime);
      osc1.frequency.exponentialRampToValueAtTime(baseFreq * 1.25, ctx.currentTime + 0.15);
      osc1.connect(gainNode);

      const osc2 = ctx.createOscillator();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(baseFreq * 1.5, ctx.currentTime);
      osc2.frequency.exponentialRampToValueAtTime(baseFreq * 1.88, ctx.currentTime + 0.15);
      osc2.connect(gainNode);

      osc1.start(ctx.currentTime);
      osc2.start(ctx.currentTime);
      osc1.stop(ctx.currentTime + 0.38);
      osc2.stop(ctx.currentTime + 0.38);

      setTimeout(() => {
        try { ctx.close(); } catch (e) {}
      }, 450);
    } catch (e) {
      console.warn('Audio warning chime:', e);
    }
  };

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
    prevThreatPercentRef.current = 0;
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
            const currentPercent = Math.round((data.risk_score || 0) * 100);
            const previousPercent = prevThreatPercentRef.current;

            // Trigger subtle warning sound on >= 50% and on every upward tick (e.g. 50 -> 51)
            if (audioAlertsEnabledRef.current && currentPercent >= 50 && currentPercent > previousPercent) {
              playSubtleWarningChime(currentPercent);
            }

            prevThreatPercentRef.current = currentPercent;
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
                  if (silenceTimerRef.current) {
                    clearTimeout(silenceTimerRef.current);
                    silenceTimerRef.current = null;
                  }
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

              // Use adjustable gap delay slider to finalize speech turn between natural gaps
              if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
              silenceTimerRef.current = setTimeout(() => {
                if (pendingInterimRef.current && pendingInterimRef.current.trim().length > 3) {
                  sendPhraseToBackend(pendingInterimRef.current);
                  pendingInterimRef.current = '';
                  setLiveInterim('');
                }
              }, speakerGapDelayMsRef.current);
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
            const maxChunks = Math.max(6, Math.round(speakerGapDelayMsRef.current / 35));
            if (pcmBufferRef.current.length > maxChunks) {
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
    <div style={{ minHeight: '100vh', backgroundColor: '#09090b', color: '#f4f4f5', fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', padding: '1.25rem 2rem' }}>
      {/* Sleek Top Navigation Bar */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', borderBottom: '1px solid #18181b', paddingBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{ width: '34px', height: '34px', borderRadius: '6px', backgroundColor: '#18181b', border: '1px solid #27272a', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f4f4f5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h1 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0, color: '#fafafa', letterSpacing: '-0.015em' }}>
                Sentinel AI
              </h1>
              <span style={{ fontSize: '0.7rem', padding: '0.12rem 0.5rem', borderRadius: '4px', backgroundColor: '#18181b', color: '#a1a1aa', border: '1px solid #27272a', fontWeight: 500 }}>
                Live Call Shield
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.72rem', color: isLive ? '#10b981' : '#71717a' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: isLive ? '#10b981' : '#52525b', display: 'inline-block' }} />
                {isLive ? 'Monitoring Active' : 'Standby'}
              </span>
            </div>
          </div>
        </div>

        {/* Global Toolbar Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          {/* Audio Chime Alert Toggle */}
          <button
            onClick={() => setAudioAlertsEnabled(!audioAlertsEnabled)}
            title="Warning chime plays when threat reaches 50% and on every upward tick"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.3rem 0.65rem',
              borderRadius: '6px',
              border: '1px solid #27272a',
              backgroundColor: audioAlertsEnabled ? 'rgba(16, 185, 129, 0.12)' : '#121215',
              color: audioAlertsEnabled ? '#34d399' : '#71717a',
              fontSize: '0.74rem',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
              {audioAlertsEnabled ? (
                <>
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
                </>
              ) : (
                <>
                  <line x1="23" y1="9" x2="17" y2="15"/>
                  <line x1="17" y1="9" x2="23" y2="15"/>
                </>
              )}
            </svg>
            {audioAlertsEnabled ? 'Chime (≥50%)' : 'Chime Off'}
          </button>

          {/* STT Engine Switch */}
          <div style={{ display: 'flex', backgroundColor: '#121215', padding: '0.2rem', borderRadius: '6px', border: '1px solid #27272a' }}>
            <button
              onClick={() => setEngine('webspeech')}
              style={{
                padding: '0.3rem 0.65rem',
                borderRadius: '4px',
                border: 'none',
                fontSize: '0.74rem',
                fontWeight: 500,
                cursor: 'pointer',
                backgroundColor: engine === 'webspeech' ? '#27272a' : 'transparent',
                color: engine === 'webspeech' ? '#fafafa' : '#71717a',
                transition: 'all 0.15s ease'
              }}
            >
              Web Speech
            </button>
            <button
              onClick={() => setEngine('scribe')}
              style={{
                padding: '0.3rem 0.65rem',
                borderRadius: '4px',
                border: 'none',
                fontSize: '0.74rem',
                fontWeight: 500,
                cursor: 'pointer',
                backgroundColor: engine === 'scribe' ? '#27272a' : 'transparent',
                color: engine === 'scribe' ? '#fafafa' : '#71717a',
                transition: 'all 0.15s ease'
              }}
            >
              Scribe v2
            </button>
          </div>

          {/* Primary Action Button */}
          <button
            onClick={isLive ? stopLiveSession : startLiveSession}
            style={{
              padding: '0.45rem 1rem',
              borderRadius: '6px',
              fontWeight: 500,
              cursor: 'pointer',
              border: isLive ? '1px solid #dc2626' : '1px solid #27272a',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              backgroundColor: isLive ? '#ef4444' : '#fafafa',
              color: isLive ? '#ffffff' : '#09090b',
              transition: 'all 0.15s ease'
            }}
          >
            {isLive ? (
              <>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="6" width="12" height="12" rx="2"/>
                </svg>
                Stop Shield
              </>
            ) : (
              <>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" y1="19" x2="12" y2="23"/>
                  <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
                Start Shield
              </>
            )}
          </button>
        </div>
      </header>

      {/* Slim Utility Bar: Voiceprint, Speaker Filter, Audio Upload */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', padding: '0.65rem 1rem', backgroundColor: '#121215', border: '1px solid #27272a', borderRadius: '6px', marginBottom: '1.25rem', fontSize: '0.78rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          {/* Voice Profile Indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <span style={{ color: '#71717a' }}>Voice Profile:</span>
            <span style={{ color: isEnrolled ? '#10b981' : '#a1a1aa', fontWeight: 500 }}>
              {isEnrolled ? 'Enrolled (Owner)' : 'Unenrolled'}
            </span>
            <button
              onClick={enrollUserVoice}
              disabled={isEnrolling}
              style={{
                padding: '0.2rem 0.55rem',
                borderRadius: '4px',
                backgroundColor: '#18181b',
                color: '#e4e4e7',
                border: '1px solid #27272a',
                fontSize: '0.72rem',
                cursor: isEnrolling ? 'not-allowed' : 'pointer'
              }}
            >
              {isEnrolling ? 'Recording 3s...' : 'Calibrate Mic'}
            </button>
          </div>

          {/* Speaker Mode Pills */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ color: '#71717a' }}>Attribution:</span>
            {(['AUTO', 'OWNER', 'CALLER'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setSpeakerMode(mode)}
                style={{
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  border: '1px solid',
                  borderColor: speakerMode === mode ? '#3b82f6' : '#27272a',
                  backgroundColor: speakerMode === mode ? '#1e3a8a' : '#18181b',
                  color: speakerMode === mode ? '#93c5fd' : '#a1a1aa',
                  fontSize: '0.7rem',
                  cursor: 'pointer',
                  fontWeight: 500
                }}
              >
                {mode === 'AUTO' ? 'Auto Biometrics' : mode === 'OWNER' ? 'You' : 'Caller'}
              </button>
            ))}
          </div>
        </div>

        {/* Right side of utility bar: File Upload & Gain */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: '#a1a1aa', cursor: 'pointer' }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>{isUploading ? 'Analyzing...' : 'Upload Audio'}</span>
            <input type="file" accept="audio/*,.wav,.mp3,.m4a" onChange={handleFileUpload} disabled={isUploading} style={{ display: 'none' }} />
          </label>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: '#71717a' }}>Gain:</span>
            <input
              type="range"
              min="1.0"
              max="4.0"
              step="0.5"
              value={micGain}
              onChange={(e) => setMicGain(parseFloat(e.target.value))}
              style={{ width: '55px', accentColor: '#3b82f6', cursor: 'pointer' }}
            />
            <span style={{ color: '#a1a1aa', fontSize: '0.7rem' }}>{micGain.toFixed(1)}x</span>
          </div>

          {/* Speaker Gap & Biometric Alignment Delay Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', borderLeft: '1px solid #27272a', paddingLeft: '0.75rem' }}>
            <span style={{ color: '#71717a' }} title="Adjust pause delay between speech turns for acoustic speaker identification">Gap Delay:</span>
            <input
              type="range"
              min="100"
              max="1200"
              step="50"
              value={speakerGapDelayMs}
              onChange={(e) => setSpeakerGapDelayMs(parseInt(e.target.value, 10))}
              style={{ width: '65px', accentColor: '#10b981', cursor: 'pointer' }}
            />
            <span style={{ color: '#a1a1aa', fontSize: '0.7rem', minWidth: '38px' }}>{speakerGapDelayMs}ms</span>
          </div>
        </div>
      </div>

      {/* Status Notifications */}
      {(enrollmentStatus || uploadFeedback) && (
        <div style={{ padding: '0.5rem 0.85rem', borderRadius: '6px', backgroundColor: '#18181b', border: '1px solid #27272a', color: '#e4e4e7', fontSize: '0.78rem', marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{enrollmentStatus || uploadFeedback}</span>
          <button onClick={() => { setEnrollmentStatus(null); setUploadFeedback(null); }} style={{ background: 'none', border: 'none', color: '#71717a', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Main 2-Column Console */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.15fr 1fr', gap: '1.25rem' }}>
        {/* Left Column: Live Audio Feed & Dialogue History */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Threat Meter Header */}
          <div style={{ padding: '1rem', backgroundColor: '#121215', border: '1px solid #27272a', borderRadius: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.45rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.78rem', color: '#71717a', fontWeight: 500 }}>THREAT ASSESSMENT</span>
                {isLive && (
                  <span style={{ fontSize: '0.68rem', padding: '0.05rem 0.35rem', borderRadius: '3px', backgroundColor: '#18181b', color: '#a1a1aa', border: '1px solid #27272a' }}>
                    Vol: {micVolume}%
                  </span>
                )}
              </div>
              <span
                style={{
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  color: threat.risk_score >= 0.75 ? '#ef4444' : threat.risk_score >= 0.45 ? '#f59e0b' : '#10b981'
                }}
              >
                {(threat.risk_score * 100).toFixed(0)}% [{threat.risk_level}]
              </span>
            </div>
            <div style={{ width: '100%', height: '5px', backgroundColor: '#18181b', borderRadius: '3px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${threat.risk_score * 100}%`,
                  height: '100%',
                  backgroundColor: threat.risk_score >= 0.75 ? '#ef4444' : threat.risk_score >= 0.45 ? '#f59e0b' : '#10b981',
                  transition: 'width 0.25s ease'
                }}
              />
            </div>
          </div>

          {/* Live Transcript / Dialogue Viewport */}
          <div style={{ padding: '1rem', backgroundColor: '#121215', border: '1px solid #27272a', borderRadius: '6px', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 600, letterSpacing: '0.03em' }}>
                CONVERSATION TIMELINE
              </span>
              {liveInterim && (
                <span style={{ fontSize: '0.7rem', color: '#3b82f6' }}>Transcribing...</span>
              )}
            </div>

            {/* Live interim speech preview */}
            {liveInterim && (
              <div style={{ padding: '0.65rem 0.85rem', backgroundColor: '#18181b', borderRadius: '4px', borderLeft: '3px solid #3b82f6', marginBottom: '0.75rem', fontSize: '0.82rem', color: '#93c5fd' }}>
                "{liveInterim}"
              </div>
            )}

            {/* Message Feed */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '340px', overflowY: 'auto' }}>
              {transcriptHistory.length === 0 && !liveInterim ? (
                <div style={{ padding: '2.5rem 1rem', textAlign: 'center', color: '#52525b', fontSize: '0.82rem' }}>
                  {isLive ? 'Listening for speech...' : 'Call shield is idle. Click "Start Shield" above to begin monitoring.'}
                </div>
              ) : (
                transcriptHistory.map((item) => {
                  const isOwner = item.speaker === 'OWNER' || item.speaker === 'VICTIM' || item.speaker === 'USER';
                  return (
                    <div
                      key={item.id}
                      style={{
                        padding: '0.65rem 0.85rem',
                        borderRadius: '6px',
                        backgroundColor: isOwner ? '#18181b' : '#1c1917',
                        borderLeft: isOwner ? '3px solid #10b981' : '3px solid #ef4444',
                        border: '1px solid #27272a',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.25rem'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span style={{ fontSize: '0.72rem', fontWeight: 600, color: isOwner ? '#10b981' : '#ef4444' }}>
                            {isOwner ? 'You (Owner)' : 'Caller'}
                          </span>
                          {item.voiceMatchScore !== undefined && item.voiceMatchScore > 0 && (
                            <span style={{ fontSize: '0.65rem', color: '#71717a' }}>
                              ({item.voiceMatchScore}% voice match)
                            </span>
                          )}
                        </div>
                        <span style={{ fontSize: '0.65rem', color: '#52525b' }}>{item.timestamp}</span>
                      </div>
                      <div style={{ fontSize: '0.82rem', color: '#e4e4e7', lineHeight: 1.45 }}>
                        "{item.text}"
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Quick Simulation Chips */}
          <div style={{ padding: '0.85rem 1rem', backgroundColor: '#121215', border: '1px solid #27272a', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.72rem', color: '#71717a', fontWeight: 600, marginBottom: '0.5rem' }}>
              TEST SCENARIOS
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.6rem' }}>
              <button
                onClick={() => sendPhraseToBackend('This is Chase Bank Fraud Department. Unauthorized transaction of $2,500 detected on your account.', 'CALLER')}
                disabled={!isLive}
                style={{ padding: '0.35rem 0.65rem', backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '4px', color: '#d4d4d8', fontSize: '0.72rem', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.4 }}
              >
                Caller: "Unauthorized $2,500"
              </button>
              <button
                onClick={() => sendPhraseToBackend('To cancel the charge right now, read me the 6-digit verification code sent to your phone immediately.', 'CALLER')}
                disabled={!isLive}
                style={{ padding: '0.35rem 0.65rem', backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '4px', color: '#d4d4d8', fontSize: '0.72rem', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.4 }}
              >
                Caller: "Read 6-digit code"
              </button>
              <button
                onClick={() => sendPhraseToBackend('This is federal officer badge 4920, an arrest warrant has been issued, do not hang up.', 'CALLER')}
                disabled={!isLive}
                style={{ padding: '0.35rem 0.65rem', backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '4px', color: '#d4d4d8', fontSize: '0.72rem', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.4 }}
              >
                Caller: "Arrest warrant"
              </button>
              <button
                onClick={() => sendPhraseToBackend('Hold on, I am opening my banking app right now to send the wire.', 'OWNER')}
                disabled={!isLive}
                style={{ padding: '0.35rem 0.65rem', backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '4px', color: '#d4d4d8', fontSize: '0.72rem', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.4 }}
              >
                You: "Opening app to wire"
              </button>
            </div>

            {/* Custom Input */}
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <input
                id="testInputOverride"
                placeholder={speakerMode === 'CALLER' ? "Test as Caller..." : "Test as You..."}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const input = e.currentTarget;
                    if (input && input.value.trim()) {
                      sendPhraseToBackend(input.value, speakerMode === 'AUTO' ? undefined : speakerMode);
                      input.value = '';
                    }
                  }
                }}
                style={{ flex: 1, padding: '0.4rem 0.65rem', borderRadius: '4px', border: '1px solid #27272a', backgroundColor: '#09090b', color: '#fafafa', fontSize: '0.76rem' }}
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
                style={{ padding: '0.4rem 0.75rem', backgroundColor: '#18181b', color: '#fafafa', border: '1px solid #27272a', borderRadius: '4px', fontSize: '0.74rem', cursor: isLive ? 'pointer' : 'not-allowed', opacity: isLive ? 1 : 0.4 }}
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Security Analysis & Actionable Guidance */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Fast-Path Critical Alert */}
          {threat.fast_path_alert && (
            <div style={{ padding: '0.85rem 1rem', borderRadius: '6px', backgroundColor: '#450a0a', border: '1px solid #dc2626', color: '#fecaca', fontSize: '0.8rem' }}>
              <div style={{ fontWeight: 600, color: '#fca5a5', marginBottom: '0.2rem' }}>
                CRITICAL: Fast-Path Credential Interception
              </div>
              <div>Authentication token or code theft demand intercepted. Refuse immediately.</div>
            </div>
          )}

          {/* Actionable Guidance Card */}
          <div style={{ padding: '1.25rem', backgroundColor: '#121215', border: '1px solid #27272a', borderRadius: '6px', flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 600, letterSpacing: '0.03em', display: 'block', marginBottom: '0.35rem' }}>
                RECOMMENDED ACTION
              </span>
              <div
                style={{
                  padding: '0.85rem 1rem',
                  backgroundColor: threat.risk_score >= 0.45 ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.06)',
                  border: threat.risk_score >= 0.45 ? '1px solid rgba(239, 68, 68, 0.25)' : '1px solid rgba(16, 185, 129, 0.2)',
                  borderRadius: '6px'
                }}
              >
                <div style={{ fontSize: '0.88rem', fontWeight: 600, color: threat.risk_score >= 0.45 ? '#f87171' : '#34d399', lineHeight: 1.45 }}>
                  {threat.recommended_action || 'Monitoring active. Speak normally into your microphone.'}
                </div>
              </div>
            </div>

            {/* Detected Indicators */}
            <div>
              <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 600, letterSpacing: '0.03em', display: 'block', marginBottom: '0.45rem' }}>
                DETECTED THREAT TACTICS
              </span>
              <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                {threat.detected_tactics && threat.detected_tactics.length > 0 ? (
                  threat.detected_tactics.map((tactic, idx) => (
                    <span
                      key={idx}
                      style={{
                        padding: '0.2rem 0.55rem',
                        backgroundColor: '#18181b',
                        border: '1px solid #27272a',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: 500,
                        color: '#f87171'
                      }}
                    >
                      {tactic}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: '0.78rem', color: '#52525b' }}>No threat indicators identified</span>
                )}
              </div>
            </div>

            {/* Evidence & Supervisor Synthesis */}
            <div style={{ marginTop: 'auto' }}>
              <span style={{ fontSize: '0.75rem', color: '#71717a', fontWeight: 600, letterSpacing: '0.03em', display: 'block', marginBottom: '0.45rem' }}>
                EVIDENCE & SUPERVISOR FINDINGS
              </span>
              <div style={{ fontSize: '0.8rem', color: '#a1a1aa', lineHeight: 1.5, backgroundColor: '#09090b', padding: '0.75rem 0.85rem', borderRadius: '4px', border: '1px solid #27272a' }}>
                {threat.explanation || 'Monitoring conversation stream for deceptive patterns...'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
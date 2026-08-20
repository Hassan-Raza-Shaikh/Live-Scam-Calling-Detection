from typing import Optional, Dict, Any, Tuple
import numpy as np

class SpeakerDiarizer:
    """
    Distinguishes between CALLER (scammer / external speaker) and OWNER / VICTIM (legitimate user).
    
    Supports:
    1. Multi-Biometric Acoustic Fingerprinting (12-bank MFCCs with CMS + Autocorrelation Pitch F0 + Formant Resonances).
    2. Hardware / Channel-based separation (Channel 0 = CALLER, Channel 1 = RECEIVER/VICTIM).
    3. Linguistic Turn Role Induction for transcript-based fallback.
    """
    
    VICTIM_CUES = [
        "why", "who is this", "what code", "i don't understand", 
        "let me check", "is this real", "my password", "how do i know",
        "wait a minute", "let me call you back", "i am confused",
        "are you sure", "how much", "i didn't make that purchase"
    ]
    
    CALLER_CUES = [
        "i am calling from", "this is officer", "fraud department",
        "you must", "immediately", "read me the", "verification code",
        "do not hang up", "transfer to", "download anydesk", "warrant for your arrest",
        "confirm your", "security verification", "safe account"
    ]

    def __init__(self):
        self.enrolled_biometrics: Optional[Dict[str, Any]] = None

    def process_frame(self, audio_data: Optional[bytes] = None, channel: int = 0) -> str:
        """
        Determines speaker from audio channel.
        Channel 0 = Remote Inbound Caller (Suspected Scammer).
        Channel 1 = Local Outbound User (Receiver / Victim).
        """
        return "CALLER" if channel == 0 else "RECEIVER"

    def _extract_biometrics(self, pcm_samples: np.ndarray, sample_rate: int = 16000) -> Dict[str, Any]:
        """Extracts 12-bank MFCCs (with CMS), fundamental pitch F0, and formant spectral peaks."""
        if len(pcm_samples) < 512:
            return {'mfcc': np.zeros(12, dtype=np.float32), 'pitch': 140.0, 'formants': np.array([500, 1500, 2500, 3500], dtype=np.float32)}
        
        audio = pcm_samples.astype(np.float32)
        # Pre-emphasis filter
        audio = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])
        
        frame_len = int(sample_rate * 0.025)
        hop_len = int(sample_rate * 0.010)
        n_frames = max(1, 1 + (len(audio) - frame_len) // hop_len)
        
        n_fft = 512
        low_freq, high_freq = 100, 7500
        mel_low = 2595 * np.log10(1 + low_freq / 700.0)
        mel_high = 2595 * np.log10(1 + high_freq / 700.0)
        mel_points = np.linspace(mel_low, mel_high, 22)
        hz_points = 700 * (10**(mel_points / 2595.0) - 1)
        bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
        
        fbank = np.zeros((20, int(n_fft / 2 + 1)))
        for m in range(1, 21):
            f_m_minus, f_m, f_m_plus = bin_points[m - 1], bin_points[m], bin_points[m + 1]
            for k in range(f_m_minus, f_m):
                fbank[m - 1, k] = (k - bin_points[m - 1]) / (bin_points[m] - bin_points[m - 1] + 1e-9)
            for k in range(f_m, f_m_plus):
                fbank[m - 1, k] = (bin_points[m + 1] - k) / (bin_points[m + 1] - bin_points[m] + 1e-9)

        frame_mfccs = []
        pitches = []
        
        for i in range(min(n_frames, 150)):
            start = i * hop_len
            frame = audio[start:start + frame_len]
            if len(frame) < frame_len:
                frame = np.pad(frame, (0, frame_len - len(frame)))
                
            windowed = frame * np.hamming(len(frame))
            mag = np.abs(np.fft.rfft(windowed, n_fft))
            pow_frames = (mag ** 2) / n_fft
            
            filter_energies = np.dot(fbank, pow_frames)
            filter_energies = np.where(filter_energies == 0, np.finfo(float).eps, filter_energies)
            log_energies = np.log(filter_energies)
            
            # 12 MFCCs (C1 to C12)
            mfcc = np.zeros(12)
            for k in range(1, 13):
                mfcc[k - 1] = np.sum(log_energies * np.cos(np.pi * k * (np.arange(20) + 0.5) / 20))
                
            # Pitch via Autocorrelation
            corr = np.correlate(windowed, windowed, mode='full')
            corr = corr[len(corr)//2:]
            min_lag = int(sample_rate / 350)
            max_lag = int(sample_rate / 75)
            if max_lag < len(corr) and len(corr) > min_lag:
                peak = min_lag + np.argmax(corr[min_lag:max_lag])
                pitch_hz = sample_rate / peak if peak > 0 else 0.0
            else:
                pitch_hz = 0.0
                
            if pitch_hz > 70:
                pitches.append(pitch_hz)
            frame_mfccs.append(mfcc)
            
        avg_mfcc = np.mean(frame_mfccs, axis=0) if frame_mfccs else np.zeros(12)
        # Cepstral Mean & Variance Normalization (CMVN)
        norm_mfcc = avg_mfcc - np.mean(avg_mfcc)
        norm_mfcc = norm_mfcc / (np.std(norm_mfcc) + 1e-6)
        
        median_pitch = float(np.median(pitches)) if pitches else 140.0
        
        # Formants & Spectral Centroid
        fft_all = np.abs(np.fft.rfft(audio[:16000], n_fft))
        freqs = np.fft.rfftfreq(n_fft, 1.0/sample_rate)
        
        # Spectral Centroid (timbre brightness)
        sum_fft = np.sum(fft_all) + 1e-9
        spectral_centroid = float(np.sum(freqs * fft_all) / sum_fft)
        
        peaks = []
        for k in range(1, len(fft_all) - 1):
            if fft_all[k] > fft_all[k-1] and fft_all[k] > fft_all[k+1] and freqs[k] > 200:
                peaks.append((fft_all[k], freqs[k]))
        peaks.sort(key=lambda x: x[0], reverse=True)
        top_formants = np.array([p[1] for p in peaks[:4]] if len(peaks) >= 4 else [500, 1500, 2500, 3500], dtype=np.float32)
        top_formants = np.sort(top_formants)
        
        return {
            'mfcc': norm_mfcc,
            'pitch': median_pitch,
            'formants': top_formants,
            'centroid': spectral_centroid
        }

    def enroll_voiceprint(self, pcm_samples: np.ndarray):
        """Enrolls user's voiceprint with multi-biometric acoustic profile."""
        if len(pcm_samples) == 0:
            return
        self.enrolled_biometrics = self._extract_biometrics(pcm_samples)

    @property
    def enrolled_voiceprint(self):
        """Backward-compatibility property for enrolled status."""
        return self.enrolled_biometrics

    def get_similarity_score(self, pcm_samples: np.ndarray) -> float:
        """Calculates multi-biometric similarity score [0.0 - 1.0] against enrolled voiceprint."""
        if self.enrolled_biometrics is None or len(pcm_samples) < 512:
            return 0.0
            
        test_bio = self._extract_biometrics(pcm_samples)
        
        # 1. MFCC Cosine Similarity (CMVN normalized)
        v1 = self.enrolled_biometrics['mfcc']
        v2 = test_bio['mfcc']
        mfcc_sim = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9))
        mfcc_score = max(0.0, min(1.0, (mfcc_sim + 1.0) / 2.0))
        
        # 2. Pitch Relative Proximity
        p_diff = abs(self.enrolled_biometrics['pitch'] - test_bio['pitch'])
        p_max = max(self.enrolled_biometrics['pitch'], test_bio['pitch'], 1.0)
        pitch_score = max(0.0, min(1.0, 1.0 - (p_diff / (p_max * 0.35))))
        
        # 3. Formant Resonance Proximity
        f_diff = np.mean(np.abs(self.enrolled_biometrics['formants'] - test_bio['formants']) / (self.enrolled_biometrics['formants'] + 1e-6))
        formant_score = max(0.0, min(1.0, 1.0 - float(f_diff * 2.0)))
        
        # 4. Spectral Centroid Timbre Proximity
        c1 = self.enrolled_biometrics.get('centroid', 1500.0)
        c2 = test_bio.get('centroid', 1500.0)
        centroid_score = max(0.0, min(1.0, 1.0 - (abs(c1 - c2) / (max(c1, c2, 1.0) * 0.5))))
        
        total_score = (0.45 * mfcc_score) + (0.25 * pitch_score) + (0.15 * formant_score) + (0.15 * centroid_score)
        return float(total_score)

    def identify_audio_speaker(self, pcm_samples: np.ndarray, threshold: float = 0.75) -> str:
        """
        Compares incoming audio against enrolled voiceprint.
        Returns 'VICTIM' (Owner) if similarity >= threshold, else 'CALLER'.
        """
        if self.enrolled_biometrics is None or len(pcm_samples) == 0:
            return "CALLER"
            
        similarity = self.get_similarity_score(pcm_samples)
        return "VICTIM" if similarity >= threshold else "CALLER"

    def predict_role_from_text(self, transcript: str) -> str:
        """Linguistic role induction fallback when audio frames are unavailable."""
        text_lower = transcript.lower()
        caller_matches = sum(1 for cue in self.CALLER_CUES if cue in text_lower)
        victim_matches = sum(1 for cue in self.VICTIM_CUES if cue in text_lower)
        
        if victim_matches > caller_matches:
            return "VICTIM"
        elif caller_matches > 0:
            return "CALLER"
        return "CALLER"
  # Default to CALLER in live monitoring mode

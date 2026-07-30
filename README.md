# Sentinel AI 🛡️: Live Scam Calling Detection System

Sentinel AI is an agentic, privacy-first, real-time scam calling detection and mitigation system. It combines high-throughput streaming speech-to-text, real-time voice activity detection (VAD), speaker diarization, and a multi-agent LangGraph supervisor system to identify, assess, and alert users against scam calls in real time.

---

## 🌟 Architecture & Workflow Overview

```
                      ┌────────────────────────┐
                      │  Live Call Audio Input │
                      └───────────┬────────────┘
                                  │
                                  ▼
                   ┌───────────────────────────────┐
                   │   Silero VAD & Preprocessing  │
                   └──────────────┬────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │                               │
                  ▼                               ▼
       ┌─────────────────────┐        ┌───────────────────────┐
       │ Speaker Diarization │        │ Streaming Whisper STT │
       └──────────┬──────────┘        └───────────┬───────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                     ┌────────────────────────┐
                     │ Fast-Path Alert Engine │ (< 200ms Instant OTP/Financial Guard)
                     └───────────┬────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │  LangGraph Workflow          │
                   │  Supervisor Engine           │
                   └──────────────┬───────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
┌───────────────────────┐ ┌───────────────┐ ┌────────────────────────┐
│ Reasoning Supervisor  │ │ Memory Superv.│ │  Consensus Supervisor  │
└───────────┬───────────┘ └───────┬───────┘ └───────────┬────────────┘
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  │
                                  ▼
                     ┌────────────────────────┐
                     │  Decision Supervisor   │
                     └───────────┬────────────┘
                                  │
        ┌─────────────────────────┼──────────────────────────┐
        │                         │                          │
        ▼                         ▼                          ▼
┌──────────────────┐    ┌────────────────────┐    ┌──────────────────────┐
│  Speech Agent    │    │ Scam Detect. Agent │    │ Soc. Engin. Agent    │
└───────┬──────────┘    └─────────┬──────────┘    └──────────┬───────────┘
        │                         │                          │
        ├──────────────┬──────────┴───────────┬──────────────┤
        │              │                      │              │
┌──────────────┐ ┌─────────────┐     ┌────────────────┐ ┌────────────────┐
│ Transcription│ │ OTP Detect. │     │ Emotion Detect.│ │ Org. Lookup    │
└───────┬──────┘ └──────┬──────┘     └───────┬────────┘ └───────┬────────┘
        └───────────────┼────────────────────┴──────────────────┘
                        │
                        ▼
            ┌────────────────────────┐
            │ Knowledge Retrieval    │
            └───────────┬────────────┘
                        │
                        ▼
            ┌────────────────────────┐
            │ Risk Scoring Agent     │
            └───────────┬────────────┘
                        │
                        ▼
            ┌────────────────────────┐
            │ Explanation Agent      │
            └───────────┬────────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │ Electron / React UI  │
             └──────────────────────┘
```

---

## ⚡ Key Features & Innovations

1. **Dual-Path Latency Architecture**:
   - **Fast-Path (< 200ms)**: Streaming keyword matching for immediate OTP/bank transfer threats.
   - **Deep-Path (Multi-Agent Supervisor)**: Multi-agent contextual graph reasoning over windowed transcripts.
2. **Speaker Diarization (`audio/diarization/`)**: Separates Caller (Suspected Scammer) from Receiver (Victim).
3. **PII Masking & Privacy (`ai/privacy/`)**: Masks credit card numbers, SSNs, and names before cloud LLM inference.
4. **LangGraph Agentic Supervisor**: Coordinated multi-agent analysis featuring 13 worker agents and 5 supervisor agents.
5. **Cross-Platform Electron + React Frontend**: Modern dark glassmorphic dashboard with live risk gauges, waveform visualizer, and actionable threat mitigation alerts.

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Docker & Docker Compose (optional for containerized deployment)

### 1. Environment Setup
```bash
cp .env.example .env
# Configure your API keys in .env
```

### 2. Backend Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/seed_database.py
```

### 3. Run Backend API & Audio Server
```bash
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

### 4. Run Frontend (React / Electron)
```bash
cd frontend/react
npm install
npm run dev

# Or launch Electron Desktop App:
cd ../electron
npm install
npm start
```

---

## 📁 Repository Directory Layout

```
sentinel-ai/
├── docs/                 # System architecture, API specs & datasets
├── frontend/             # Electron & React dashboard UI
├── backend/              # FastAPI server, WebSockets & services
├── ai/                   # LangGraph supervisor-worker state machine
├── audio/                # VAD, Whisper STT, Diarization & TTS
├── knowledge/            # Scam pattern databases & org profiles
├── datasets/             # Training, evaluation & synthetic data
├── models/               # Weights and cache directory
├── tests/                # Unit, integration & end-to-end tests
└── scripts/              # Utility scripts for setup & evaluation
```

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

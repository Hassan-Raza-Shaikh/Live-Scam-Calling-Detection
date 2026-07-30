# Sentinel AI - System Architecture Specifications

## 1. Overview

Sentinel AI is designed for **low-latency (< 200ms fast alert)** and **deep-context agentic reasoning** during live voice telephone calls to safeguard users against financial fraud, imposter scams, OTP theft, and social engineering attacks.

---

## 2. Multi-Tier Agentic Supervisor Workflow

The core reasoning engine is built on **LangGraph**. The workflow comprises two layers of agents: **Supervisors** and **Workers**.

### 2.1 Supervisors (Control Layer)
1. **Workflow Supervisor**: Serves as the primary entry point orchestrating state transitions.
2. **Memory Supervisor**: Manages windowed short-term conversation memory and long-term vector embeddings.
3. **Reasoning Supervisor**: Coordinates multi-perspective worker reasoning.
4. **Consensus Supervisor**: Aggregates outputs from fraud, emotion, and urgency workers to form a coherent threat hypothesis.
5. **Decision Supervisor**: Computes the final actionable risk score, decision matrix state, and user alert payload.

### 2.2 Worker Agents (Execution Layer)
- **Speech Agent**: Handles speech quality, background noise, and voice stress signals.
- **Transcription Agent**: Receives raw VAD segments and produces stream-aligned transcripts.
- **Scam Detection Agent**: Detects known scam taxonomies (banking, tech support, government).
- **Social Engineering Agent**: Identifies psychological manipulation techniques (authority claim, isolation, fear).
- **Verification Agent**: Validates caller assertions against organization knowledge banks.
- **Organization Lookup Agent**: Queries legit bank, telecom, and government entity registries.
- **Knowledge Retrieval Agent**: Performs vector semantic search on historical scam database patterns.
- **Urgency Detection Agent**: Measures time pressure and artificial emergency tactics.
- **Emotion Detection Agent**: Analyzes acoustic features and textual affect (fear, panic, high pressure).
- **OTP Detection Agent**: Fast-path detection of direct requests for One-Time Passwords, PINs, or verification codes.
- **Financial Request Agent**: Flags requests for bank transfers, gift cards, crypto, or wire payments.
- **Risk Scoring Agent**: Evaluates mathematical threat weights across all worker outputs.
- **Explanation Agent**: Synthesizes human-readable risk explanations and recommended safety actions.

---

## 3. Dual-Path Execution Model

| Path | Processing Latency | Components | Primary Goal |
|---|---|---|---|
| **Fast-Path** | < 200ms | VAD $\rightarrow$ Streaming Whisper $\rightarrow$ RegEx/Keyword OTP Guard | Immediate emergency pop-up if OTP/Wire demand is detected |
| **Deep-Path** | 1.5s - 3s | Transcripts $\rightarrow$ LangGraph Supervisors $\rightarrow$ RAG Vector Store $\rightarrow$ Multi-Agent Reasoning | Contextual analysis, confidence scoring, explanation generation |

---

## 4. Security & Privacy

1. **Local Audio Stream Processing**: Audio buffers remain on device memory and are processed via local Silero VAD.
2. **PII Masking**: Credit cards, SSNs, and personal identity items are masked in `ai/privacy/` before external model inference.

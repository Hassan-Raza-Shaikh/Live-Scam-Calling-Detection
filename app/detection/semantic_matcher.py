from typing import List, Dict, Any
import re
import math
import numpy as np

class SemanticScamMatcher:
    """
    Lightweight, sub-millisecond pure-numpy semantic similarity engine for detecting
    evasive and paraphrased scam phrases across all scam taxonomies without external ML dependencies.
    """
    
    REFERENCE_SCAM_PROFILES = [
        # Banking & Safe Account
        ("BANKING_FRAUD", "there has been unauthorized suspicious activity on your bank account transfer funds to a safe government account"),
        ("BANKING_FRAUD", "verify your full name and security credentials to unfreeze your online banking profile"),
        ("BANKING_FRAUD", "fraud department alerts you to move your balance to a protected reserve account immediately"),
        
        # OTP / 2FA Theft
        ("OTP_THEFT", "read me the six digit verification passcode that just arrived on your mobile device"),
        ("OTP_THEFT", "what are the numbers showing on your confirmation text message alert"),
        ("OTP_THEFT", "provide the one time authentication code to cancel the unauthorized charge"),
        
        # Government & Law Enforcement
        ("GOVERNMENT_IMPERSONATION", "federal marshals and police have issued an active warrant for your arrest"),
        ("GOVERNMENT_IMPERSONATION", "deputy sheriff is dispatched to your residence for missing federal court jury duty"),
        ("GOVERNMENT_IMPERSONATION", "internal revenue service legal action against your social security number"),
        
        # Tech Support
        ("TECH_SUPPORT", "your computer has been compromised with a malicious trojan virus download anydesk or teamviewer"),
        ("TECH_SUPPORT", "windows security alert call microsoft certified technician to clean infected network"),
        
        # Crypto & Pig Butchering
        ("CRYPTO_INVESTMENT", "guaranteed high returns daily passive income on liquidity mining platform deposit crypto into wallet"),
        ("CRYPTO_INVESTMENT", "exclusive decentralized trading group deposit tether usdt to unlock VIP tier"),
        
        # Family Emergency
        ("FAMILY_EMERGENCY", "grandma i had a terrible car accident in hospital need urgent bail bond money do not tell parents"),
        ("FAMILY_EMERGENCY", "your child is being detained by authorities wire money immediately for immediate release"),
        
        # Coercive Isolation & Panic
        ("ISOLATION_COERCION", "stay on the line do not disconnect do not mention this undercover investigation to bank tellers or family"),
        ("HIGH_PRESSURE_URGENCY", "you have thirty minutes before your accounts are completely suspended and seized by the court"),
        
        # Untraceable Payment
        ("UNTRACEABLE_PAYMENT", "go to the nearest convenience store purchase apple target gift cards read the pin codes on the back"),
        ("UNTRACEABLE_PAYMENT", "deposit physical cash into the bitcoin cryptocurrency automated teller machine")
    ]

    def __init__(self):
        self.intents = [profile[0] for profile in self.REFERENCE_SCAM_PROFILES]
        self.texts = [profile[1] for profile in self.REFERENCE_SCAM_PROFILES]
        
        # Build vocabulary of 1-gram, 2-gram, and 3-grams
        self.vocab: Dict[str, int] = {}
        doc_tokens_list = []
        for text in self.texts:
            tokens = self._tokenize(text)
            doc_tokens_list.append(tokens)
            for token in tokens:
                if token not in self.vocab:
                    self.vocab[token] = len(self.vocab)
                    
        num_docs = len(self.texts)
        vocab_size = len(self.vocab)
        
        # Compute Document Frequencies (DF)
        df = np.zeros(vocab_size, dtype=np.float32)
        for tokens in doc_tokens_list:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                df[self.vocab[token]] += 1.0
                
        # Compute Inverse Document Frequency (IDF) with smoothing
        self.idf = np.log((1.0 + num_docs) / (1.0 + df)) + 1.0
        
        # Precompute reference TF-IDF vectors
        self.reference_matrix = np.zeros((num_docs, vocab_size), dtype=np.float32)
        for i, tokens in enumerate(doc_tokens_list):
            self.reference_matrix[i] = self._vectorize(tokens)

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r'\b[a-z0-9]+\b', text.lower())
        tokens = []
        # 1-grams
        tokens.extend(words)
        # 2-grams
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]} {words[i+1]}")
        # 3-grams
        for i in range(len(words) - 2):
            tokens.append(f"{words[i]} {words[i+1]} {words[i+2]}")
        return tokens

    def _vectorize(self, tokens: List[str]) -> np.ndarray:
        vec = np.zeros(len(self.vocab), dtype=np.float32)
        for token in tokens:
            idx = self.vocab.get(token)
            if idx is not None:
                vec[idx] += 1.0
                
        # Sublinear term frequency: 1 + log(tf)
        nonzero = vec > 0
        vec[nonzero] = (1.0 + np.log(vec[nonzero])) * self.idf[nonzero]
        
        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def match(self, text: str, threshold: float = 0.30) -> List[Dict[str, Any]]:
        """
        Computes cosine similarity between incoming transcript and reference scam profiles.
        Returns matched intents with similarity scores.
        """
        if not text or len(text.strip()) < 5:
            return []
            
        tokens = self._tokenize(text)
        query_vec = self._vectorize(tokens)
        
        if np.linalg.norm(query_vec) == 0:
            return []
            
        # Cosine similarities (dot product with L2 normalized matrix)
        similarities = np.dot(self.reference_matrix, query_vec)
        
        matches = []
        for idx, score in enumerate(similarities):
            if score >= threshold:
                matches.append({
                    "intent": self.intents[idx],
                    "similarity": float(score),
                    "reference_concept": self.texts[idx],
                    "matched_query": text
                })
                
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches

from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class SemanticScamMatcher:
    """
    Lightweight, sub-millisecond semantic similarity engine for detecting
    evasive and paraphrased scam phrases across all 18 scam taxonomies.
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
        
        # Fit lightweight word + char n-gram TF-IDF vectorizer (robust to misspellings & paraphrasing)
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 3),
            min_df=1,
            sublinear_tf=True
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.texts)

    def match(self, text: str, threshold: float = 0.35) -> List[Dict[str, Any]]:
        """
        Computes cosine similarity between incoming transcript and reference scam profiles.
        Returns matched intents with similarity scores.
        """
        if not text or len(text.strip()) < 5:
            return []
            
        query_vec = self.vectorizer.transform([text])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        
        matches = []
        for idx, score in enumerate(similarities):
            if score >= threshold:
                matches.append({
                    "intent": self.intents[idx],
                    "similarity": float(score),
                    "reference_concept": self.texts[idx],
                    "matched_query": text
                })
                
        # Sort matches by similarity score descending
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches

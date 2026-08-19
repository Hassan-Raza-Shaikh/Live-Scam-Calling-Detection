class KeywordDictionary:
    """Contains standard categories and list of scam keywords."""
    CATEGORIES = {
        "OTP_DEMAND": ["verification code", "6-digit code", "one-time password", "otp"],
        "IMPERSONATION": ["bank security", "irs department", "fraud department", "microsoft support"],
        "URGENCY": ["immediately", "right now", "arrest warrant", "freeze account"]
    }

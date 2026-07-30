import re

class PIIMasker:
    """Masks sensitive personal data (credit card numbers, SSNs, OTPs, phone numbers) before cloud processing."""
    
    CARD_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    OTP_PATTERN = re.compile(r'\b\d{6}\b')
    PHONE_PATTERN = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')

    @classmethod
    def mask(cls, text: str) -> str:
        if not text:
            return ""
        text = cls.CARD_PATTERN.sub('[CARD_NUMBER_REDACTED]', text)
        text = cls.SSN_PATTERN.sub('[SSN_REDACTED]', text)
        text = cls.PHONE_PATTERN.sub('[PHONE_REDACTED]', text)
        # Keep track of OTP patterns for detection, but redact raw numbers
        text = cls.OTP_PATTERN.sub('[6-DIGIT_CODE]', text)
        return text

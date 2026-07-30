import unittest
from ai.privacy.pii_masker import PIIMasker

class TestPIIMasker(unittest.TestCase):
    def test_card_and_otp_redaction(self):
        raw = "My card number is 4532-1234-5678-9012 and my code is 123456."
        masked = PIIMasker.mask(raw)
        self.assertNotIn("4532", masked)
        self.assertIn("[CARD_NUMBER_REDACTED]", masked)
        self.assertIn("[6-DIGIT_CODE]", masked)

if __name__ == "__main__":
    unittest.main()

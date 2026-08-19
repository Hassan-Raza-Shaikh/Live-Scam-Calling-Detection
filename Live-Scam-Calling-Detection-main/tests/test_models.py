import pytest
from app.models.classifier import ScamClassifier

def test_scam_classifier():
    classifier = ScamClassifier()
    # Test classifier outputs 0.0 mock prediction
    assert classifier.predict({}) == 0.0

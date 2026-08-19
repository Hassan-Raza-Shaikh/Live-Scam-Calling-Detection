import pytest
import yaml
from pathlib import Path
from app.detection.patterns.loader import PatternLoader
from app.detection.exceptions import PatternLoadError

def test_loader_real_database():
    # Load the real YAML database from the package
    db_dir = Path(__file__).parent.parent / "patterns" / "database"
    loader = PatternLoader(db_dir)
    database = loader.load()
    
    assert len(database.rules) >= 8
    assert "OTP_REQUEST" in database.rules
    assert "BANKING_FRAUD" in database.rules
    
    # Assert cached reload works
    database2 = loader.load()
    assert database is database2

def test_loader_validation_missing_field(tmp_path):
    # Create invalid YAML file missing 'intent'
    invalid_data = {
        "description": "Missing intent field",
        "category": "Testing",
        "weight": 10,
        "priority": "low"
    }
    
    file_path = tmp_path / "invalid.yaml"
    with open(file_path, "w") as f:
        yaml.dump(invalid_data, f)
        
    loader = PatternLoader(tmp_path)
    with pytest.raises(PatternLoadError) as exc_info:
        loader.load()
    
    assert "Missing required field 'intent'" in str(exc_info.value)

def test_loader_validation_invalid_type(tmp_path):
    # Weight must be integer
    invalid_data = {
        "intent": "TEST",
        "description": "Invalid weight type",
        "category": "Testing",
        "weight": "not_an_int",
        "priority": "low"
    }
    
    file_path = tmp_path / "invalid.yaml"
    with open(file_path, "w") as f:
        yaml.dump(invalid_data, f)
        
    loader = PatternLoader(tmp_path)
    with pytest.raises(PatternLoadError) as exc_info:
        loader.load()
        
    assert "Field 'weight' must be an integer" in str(exc_info.value)

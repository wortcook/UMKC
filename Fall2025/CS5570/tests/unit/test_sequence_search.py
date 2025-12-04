"""
Unit tests for sequence search functionality
"""

import pytest
from opengenome.analysis.sequence_search import SequenceSearcher


def test_reverse_complement():
    """Test reverse complement calculation"""
    assert SequenceSearcher.reverse_complement("ACGT") == "ACGT"
    assert SequenceSearcher.reverse_complement("AAAA") == "TTTT"
    assert SequenceSearcher.reverse_complement("ACGACG") == "CGTCGT"
    assert SequenceSearcher.reverse_complement("ATCG") == "CGAT"
    
    # Test with mixed case
    assert SequenceSearcher.reverse_complement("acgt") == "acgt"
    assert SequenceSearcher.reverse_complement("AcGt") == "AcGt"
    
    # Test with N (ambiguous base)
    assert SequenceSearcher.reverse_complement("ACGTN") == "NACGT"


def test_validate_dna_pattern_valid():
    """Test validation of valid DNA patterns"""
    # Should not raise for valid patterns
    SequenceSearcher.validate_dna_pattern("ACGT")
    SequenceSearcher.validate_dna_pattern("acgt")
    SequenceSearcher.validate_dna_pattern("ACGTNNACGT")
    SequenceSearcher.validate_dna_pattern("AAA")


def test_validate_dna_pattern_invalid():
    """Test validation catches invalid patterns"""
    # Should raise ValueError for invalid patterns
    with pytest.raises(ValueError, match="empty"):
        SequenceSearcher.validate_dna_pattern("")
    
    with pytest.raises(ValueError, match="invalid.*characters"):
        SequenceSearcher.validate_dna_pattern("ACGTX")
    
    with pytest.raises(ValueError, match="invalid.*characters"):
        SequenceSearcher.validate_dna_pattern("ACG123")
    
    with pytest.raises(ValueError, match="invalid.*characters"):
        SequenceSearcher.validate_dna_pattern("ACG-TGA")
    
    with pytest.raises(ValueError, match="invalid.*characters"):
        SequenceSearcher.validate_dna_pattern("ACG'TGA")


def test_validate_dna_pattern_warnings(caplog):
    """Test that warnings are logged for edge cases"""
    import logging
    
    # Short pattern warning
    with caplog.at_level(logging.WARNING):
        SequenceSearcher.validate_dna_pattern("AC")
        assert "Short pattern" in caplog.text
    
    caplog.clear()
    
    # Long pattern warning
    with caplog.at_level(logging.WARNING):
        SequenceSearcher.validate_dna_pattern("A" * 101)
        assert "Long pattern" in caplog.text


def test_sql_escape():
    """Test that patterns with quotes are handled correctly"""
    # This would be tested in integration tests with actual Spark
    # Here we just verify the validation doesn't reject valid DNA with special handling
    
    # Patterns that could cause SQL injection should still be validated
    pattern = "ACGT"  # Normal pattern
    SequenceSearcher.validate_dna_pattern(pattern)
    
    # Even if someone tries quotes, validation should catch non-DNA characters
    with pytest.raises(ValueError):
        SequenceSearcher.validate_dna_pattern("ACG'T")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

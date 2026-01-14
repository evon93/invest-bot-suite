"""
tests/test_mock_ohlcv_edge_cases_3L3.py

Edge-case tests for MockOHLCVClient and OHLCV validation.

AG-3L-3-1: Validates strict contract enforcement:
- Out-of-order timestamps → OHLCVValidationError
- Duplicate timestamps → OHLCVValidationError
- Gaps → warning/flag but data returned
- Invalid OHLC relationships → OHLCVValidationError
"""

import pytest
import logging

from engine.market_data.ccxt_adapter import (
    MockOHLCVClient,
    OHLCVValidationError,
    validate_ohlcv_data,
)


class TestOutOfOrderTimestamps:
    """Tests for out-of-order timestamp handling."""
    
    def test_out_of_order_raises_error(self):
        """Out-of-order timestamps raise OHLCVValidationError."""
        # Second bar has earlier timestamp than first
        out_of_order_data = [
            [1705280400000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],  # Later
            [1705276800000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],  # Earlier
        ]
        
        with pytest.raises(OHLCVValidationError, match="out-of-order"):
            MockOHLCVClient(data=out_of_order_data, strict=True)
    
    def test_out_of_order_validation_function(self):
        """validate_ohlcv_data raises on out-of-order."""
        data = [
            [1705280400000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],
            [1705276800000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],
        ]
        
        with pytest.raises(OHLCVValidationError, match="out-of-order"):
            validate_ohlcv_data(data, strict=True)
    
    def test_out_of_order_non_strict_logs_issue(self):
        """Non-strict mode logs issue but doesn't raise."""
        data = [
            [1705280400000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],
            [1705276800000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],
        ]
        
        result = validate_ohlcv_data(data, strict=False)
        
        assert result['valid'] is False
        assert len(result['issues']) > 0
        assert any("out-of-order" in issue for issue in result['issues'])


class TestDuplicateTimestamps:
    """Tests for duplicate timestamp handling."""
    
    def test_duplicate_ts_raises_error(self):
        """Duplicate timestamps raise OHLCVValidationError."""
        duplicate_data = [
            [1705276800000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],
            [1705276800000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],  # Same ts
        ]
        
        with pytest.raises(OHLCVValidationError, match="duplicate"):
            MockOHLCVClient(data=duplicate_data, strict=True)
    
    def test_duplicate_validation_function(self):
        """validate_ohlcv_data raises on duplicates."""
        data = [
            [1705276800000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],
            [1705276800000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],
        ]
        
        with pytest.raises(OHLCVValidationError, match="duplicate"):
            validate_ohlcv_data(data, strict=True)


class TestGapsHandling:
    """Tests for temporal gap detection."""
    
    def test_gaps_detected_but_data_returned(self):
        """Gaps are flagged but data is still usable."""
        # Normal interval is 1 hour (3600000ms), gap of 4 hours after multiple regular bars
        gapped_data = [
            [1705276800000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],  # 00:00
            [1705280400000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],  # 01:00 (+1h)
            [1705284000000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],  # 02:00 (+1h)
            [1705287600000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],  # 03:00 (+1h)
            [1705306800000, 42600.0, 42900.0, 42400.0, 42700.0, 800.0],   # 08:00 (+5h gap)
        ]
        
        client = MockOHLCVClient(data=gapped_data, strict=True)
        
        assert client.has_gaps is True
        
        # Data should still be usable
        result = client.fetch_ohlcv("BTC/USDT")
        assert len(result) == 5
    
    def test_no_gaps_in_regular_data(self):
        """Regular data without gaps is flagged correctly."""
        regular_data = [
            [1705276800000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],
            [1705280400000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],
            [1705284000000, 42600.0, 42900.0, 42400.0, 42700.0, 800.0],
        ]
        
        client = MockOHLCVClient(data=regular_data, strict=True)
        
        assert client.has_gaps is False


class TestOHLCRelationships:
    """Tests for OHLC relationship validation."""
    
    def test_high_less_than_open_close_raises(self):
        """High < max(open, close) raises error."""
        bad_data = [
            [1705276800000, 42000.0, 41000.0, 41800.0, 42300.0, 1000.0],  # high=41000 < open=42000
        ]
        
        with pytest.raises(OHLCVValidationError, match="high.*< max"):
            MockOHLCVClient(data=bad_data, strict=True)
    
    def test_low_greater_than_open_close_raises(self):
        """Low > min(open, close) raises error."""
        bad_data = [
            [1705276800000, 42000.0, 42500.0, 43000.0, 42300.0, 1000.0],  # low=43000 > min(42000, 42300)
        ]
        
        with pytest.raises(OHLCVValidationError, match="low.*> min"):
            MockOHLCVClient(data=bad_data, strict=True)
    
    def test_negative_volume_raises(self):
        """Negative volume raises error."""
        bad_data = [
            [1705276800000, 42000.0, 42500.0, 41800.0, 42300.0, -100.0],  # negative volume
        ]
        
        with pytest.raises(OHLCVValidationError, match="negative volume"):
            MockOHLCVClient(data=bad_data, strict=True)


class TestValidData:
    """Tests for valid data handling."""
    
    def test_valid_data_passes(self):
        """Valid data passes validation without errors."""
        valid_data = [
            [1705276800000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],
            [1705280400000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],
            [1705284000000, 42600.0, 42900.0, 42400.0, 42700.0, 800.0],
        ]
        
        # Should not raise
        client = MockOHLCVClient(data=valid_data, strict=True)
        
        result = client.fetch_ohlcv("BTC/USDT")
        assert len(result) == 3
    
    def test_generated_data_always_valid(self):
        """Auto-generated mock data is always valid."""
        client = MockOHLCVClient(seed=42, n_bars=50)
        
        data = client.fetch_ohlcv("BTC/USDT")
        
        # Validate generated data
        result = validate_ohlcv_data(data, strict=True)
        
        assert result['valid'] is True
        assert result['has_gaps'] is False
        assert len(result['issues']) == 0
    
    def test_monotonic_increasing_property(self):
        """Generated data has strictly increasing timestamps."""
        client = MockOHLCVClient(seed=123, n_bars=100)
        
        data = client.fetch_ohlcv("BTC/USDT")
        
        for i in range(1, len(data)):
            assert data[i][0] > data[i-1][0], f"Non-monotonic at index {i}"


class TestEmptyData:
    """Tests for empty data handling."""
    
    def test_empty_data_passes_validation(self):
        """Empty data list passes validation."""
        result = validate_ohlcv_data([], strict=True)
        
        assert result['valid'] is True
        assert result['has_gaps'] is False
    
    def test_single_candle_valid(self):
        """Single candle data is valid."""
        data = [
            [1705276800000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],
        ]
        
        client = MockOHLCVClient(data=data, strict=True)
        result = client.fetch_ohlcv("BTC/USDT")
        
        assert len(result) == 1


class TestNonStrictMode:
    """Tests for non-strict mode behavior."""
    
    def test_non_strict_collects_all_issues(self):
        """Non-strict mode collects all issues without raising."""
        bad_data = [
            [1705280400000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],  # Out of order
            [1705276800000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],  # Earlier
            [1705276800000, 42600.0, 42900.0, 42400.0, 42700.0, 800.0],   # Duplicate
        ]
        
        result = validate_ohlcv_data(bad_data, strict=False)
        
        assert result['valid'] is False
        # Should have multiple issues
        assert len(result['issues']) >= 2

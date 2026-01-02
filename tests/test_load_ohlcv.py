"""
test_load_ohlcv.py — Tests for OHLCV loader

Uses synthetic fixtures, no external data files.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Add tools to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.load_ohlcv import load_ohlcv, CANONICAL_COLUMNS, summarize


class TestLoadOHLCV:
    """Tests for load_ohlcv function."""

    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create sample CSV file with OHLCV data."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10, freq="D"),
            "open": [100 + i for i in range(10)],
            "high": [105 + i for i in range(10)],
            "low": [95 + i for i in range(10)],
            "close": [102 + i for i in range(10)],
            "volume": [1000 * (i + 1) for i in range(10)],
        })
        path = tmp_path / "test_ohlcv.csv"
        df.to_csv(path, index=False)
        return path

    @pytest.fixture
    def sample_csv_aliased(self, tmp_path):
        """Create sample CSV with aliased column names."""
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="D"),
            "o": [100, 101, 102, 103, 104],
            "h": [105, 106, 107, 108, 109],
            "l": [95, 96, 97, 98, 99],
            "c": [102, 103, 104, 105, 106],
            "vol": [1000, 2000, 3000, 4000, 5000],
        })
        path = tmp_path / "test_aliased.csv"
        df.to_csv(path, index=False)
        return path

    @pytest.fixture
    def sample_csv_unsorted(self, tmp_path):
        """Create CSV with unsorted dates."""
        df = pd.DataFrame({
            "date": ["2024-01-05", "2024-01-01", "2024-01-03", "2024-01-02", "2024-01-04"],
            "open": [100, 101, 102, 103, 104],
            "high": [105, 106, 107, 108, 109],
            "low": [95, 96, 97, 98, 99],
            "close": [102, 103, 104, 105, 106],
            "volume": [1000, 2000, 3000, 4000, 5000],
        })
        path = tmp_path / "test_unsorted.csv"
        df.to_csv(path, index=False)
        return path

    @pytest.fixture
    def sample_csv_with_dupes(self, tmp_path):
        """Create CSV with duplicate dates."""
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"],
            "open": [100, 101, 102, 103, 104],
            "high": [105, 106, 107, 108, 109],
            "low": [95, 96, 97, 98, 99],
            "close": [102, 103, 104, 105, 106],
            "volume": [1000, 2000, 3000, 4000, 5000],
        })
        path = tmp_path / "test_dupes.csv"
        df.to_csv(path, index=False)
        return path

    def test_load_csv_basic(self, sample_csv):
        """Load basic CSV file."""
        df = load_ohlcv(sample_csv)
        
        assert len(df) == 10
        assert list(df.columns) == CANONICAL_COLUMNS
        assert df["date"].dtype == "datetime64[ns]"
        assert df["close"].dtype == "float64"

    def test_load_csv_aliased_columns(self, sample_csv_aliased):
        """Load CSV with aliased column names."""
        df = load_ohlcv(sample_csv_aliased)
        
        assert len(df) == 5
        assert list(df.columns) == CANONICAL_COLUMNS
        # Check values preserved
        assert df["close"].iloc[0] == 102.0

    def test_load_csv_sorted(self, sample_csv_unsorted):
        """Verify output is sorted by date ascending."""
        df = load_ohlcv(sample_csv_unsorted)
        
        dates = df["date"].tolist()
        assert dates == sorted(dates)

    def test_load_csv_deduplicates(self, sample_csv_with_dupes):
        """Verify duplicates are removed (keep last)."""
        df = load_ohlcv(sample_csv_with_dupes)
        
        # Should have 3 unique dates
        assert len(df) == 3
        # Verify dates are unique
        assert df["date"].nunique() == 3

    def test_file_not_found(self):
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_ohlcv("/nonexistent/path/file.csv")

    def test_missing_column(self, tmp_path):
        """Raise ValueError if required column missing."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [100, 101, 102],
            # Missing: high, low, close, volume
        })
        path = tmp_path / "missing_cols.csv"
        df.to_csv(path, index=False)
        
        with pytest.raises(ValueError, match="Missing required column"):
            load_ohlcv(path)

    def test_summarize(self, sample_csv):
        """Test summarize function."""
        df = load_ohlcv(sample_csv)
        s = summarize(df, n_dupes=0)
        
        assert s["n_rows"] == 10
        assert s["date_min"] is not None
        assert s["date_max"] is not None
        assert "n_duplicates_removed" in s


class TestParquet:
    """Tests for Parquet support (skip if engine not available)."""

    @pytest.fixture
    def sample_parquet(self, tmp_path):
        """Create sample Parquet file if engine available."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [100, 101, 102, 103, 104],
            "high": [105, 106, 107, 108, 109],
            "low": [95, 96, 97, 98, 99],
            "close": [102, 103, 104, 105, 106],
            "volume": [1000, 2000, 3000, 4000, 5000],
        })
        path = tmp_path / "test_ohlcv.parquet"
        try:
            df.to_parquet(path)
            return path
        except ImportError:
            pytest.skip("Parquet engine not available")

    def test_load_parquet(self, sample_parquet):
        """Load Parquet file."""
        df = load_ohlcv(sample_parquet)
        
        assert len(df) == 5
        assert list(df.columns) == CANONICAL_COLUMNS


class TestCLI:
    """Tests for CLI interface."""

    @pytest.fixture
    def cli_csv(self, tmp_path):
        """Create CSV for CLI test."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [100, 101, 102, 103, 104],
            "high": [105, 106, 107, 108, 109],
            "low": [95, 96, 97, 98, 99],
            "close": [102, 103, 104, 105, 106],
            "volume": [1000, 2000, 3000, 4000, 5000],
        })
        path = tmp_path / "cli_test.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    def test_cli_exit_code_0(self, cli_csv):
        """CLI returns exit code 0 on success."""
        import os
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "load_ohlcv.py"), "--path", str(cli_csv)],
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "OHLCV Summary" in result.stdout
        assert "Rows: 5" in result.stdout

    def test_cli_missing_file(self):
        """CLI returns exit code 1 on missing file."""
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "load_ohlcv.py"), "--path", "/nonexistent.csv"],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 1
        assert "ERROR" in result.stderr or "not found" in result.stderr.lower()

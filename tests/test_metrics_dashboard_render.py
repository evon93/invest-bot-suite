"""
tests/test_metrics_dashboard_render.py

Tests for metrics dashboard HTML rendering (AG-3H-3-1).

Validates:
- HTML is generated from summary
- Contains expected sections and keywords
- Handles empty/minimal data gracefully
"""

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from render_metrics_dashboard_3H import load_summary, tail_ndjson_files, render_html


class TestLoadSummary:
    """Test summary file loading."""
    
    def test_load_existing_summary(self, tmp_path: Path):
        """Should load valid summary JSON."""
        summary = {
            "processed": 100,
            "filled": 50,
            "stages_by_name": {"strategy": {"count": 10, "p50_ms": 1.5}},
        }
        (tmp_path / "metrics_summary.json").write_text(json.dumps(summary))
        
        loaded = load_summary(tmp_path)
        
        assert loaded["processed"] == 100
        assert loaded["filled"] == 50
        assert "strategy" in loaded["stages_by_name"]
    
    def test_load_missing_summary(self, tmp_path: Path):
        """Should return empty dict if summary doesn't exist."""
        loaded = load_summary(tmp_path)
        assert loaded == {}


class TestTailNdjson:
    """Test NDJSON tailing functionality."""
    
    def test_tail_single_file(self, tmp_path: Path):
        """Should read events from single metrics.ndjson."""
        events = [{"stage": "test", "i": i} for i in range(5)]
        ndjson = "\n".join(json.dumps(e) for e in events) + "\n"
        (tmp_path / "metrics.ndjson").write_text(ndjson)
        
        loaded = tail_ndjson_files(tmp_path, max_lines=100)
        
        assert len(loaded) == 5
        assert loaded[0]["i"] == 0
        assert loaded[4]["i"] == 4
    
    def test_tail_rotated_files(self, tmp_path: Path):
        """Should read rotated files in order (.1, .2, then main)."""
        # .1 is oldest
        (tmp_path / "metrics.ndjson.1").write_text(json.dumps({"order": 1}) + "\n")
        # .2 is next
        (tmp_path / "metrics.ndjson.2").write_text(json.dumps({"order": 2}) + "\n")
        # main is newest
        (tmp_path / "metrics.ndjson").write_text(json.dumps({"order": 3}) + "\n")
        
        loaded = tail_ndjson_files(tmp_path, max_lines=100)
        
        assert len(loaded) == 3
        assert loaded[0]["order"] == 1  # oldest first
        assert loaded[1]["order"] == 2
        assert loaded[2]["order"] == 3  # newest last
    
    def test_tail_limits_lines(self, tmp_path: Path):
        """Should respect max_lines limit."""
        events = [{"i": i} for i in range(100)]
        ndjson = "\n".join(json.dumps(e) for e in events) + "\n"
        (tmp_path / "metrics.ndjson").write_text(ndjson)
        
        loaded = tail_ndjson_files(tmp_path, max_lines=10)
        
        assert len(loaded) == 10
        # Should be last 10 events
        assert loaded[0]["i"] == 90
        assert loaded[9]["i"] == 99
    
    def test_tail_empty_directory(self, tmp_path: Path):
        """Should return empty list if no files exist."""
        loaded = tail_ndjson_files(tmp_path, max_lines=100)
        assert loaded == []


class TestRenderHtml:
    """Test HTML rendering."""
    
    def test_render_with_data(self, tmp_path: Path):
        """Should render HTML with all sections."""
        summary = {
            "processed": 100,
            "allowed": 80,
            "rejected": 15,
            "filled": 50,
            "errors": 5,
            "retries": 2,
            "dupes_filtered": 0,
            "latency_p50_ms": 1.5,
            "latency_p95_ms": 5.0,
            "latency_count": 100,
            "stage_events_count": 200,
            "stages_by_name": {
                "strategy": {"count": 100, "p50_ms": 0.5, "p95_ms": 1.0},
                "risk": {"count": 80, "p50_ms": 0.3, "p95_ms": 0.8},
            },
            "outcomes_by_stage": {
                "strategy": {"ok": 100},
                "risk": {"ok": 75, "rejected": 5},
            },
            "errors_by_reason": {"timeout": 3, "network": 2},
            "rejects_by_reason": {"dd_guardrail": 10, "max_position": 5},
        }
        events = [
            {"stage": "strategy", "step_id": 1, "trace_id": "abc123", "outcome": "ok", "dt": 0.001},
            {"stage": "risk", "step_id": 2, "trace_id": "def456", "outcome": "rejected", "dt": 0.002},
        ]
        
        html = render_html(summary, events, tmp_path)
        
        # Check structure
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        
        # Check sections
        assert "Overview" in html
        assert "Latency" in html
        assert "Stages" in html
        assert "Recent Events" in html
        
        # Check data
        assert "100" in html  # processed
        assert "50" in html   # filled
        assert "strategy" in html
        assert "risk" in html
        assert "timeout" in html
        assert "dd_guardrail" in html
    
    def test_render_empty_summary(self, tmp_path: Path):
        """Should handle empty summary gracefully."""
        html = render_html({}, [], tmp_path)
        
        assert "<!DOCTYPE html>" in html
        assert "No stage data available" in html
        assert "No events available" in html
    
    def test_render_escapes_html(self, tmp_path: Path):
        """Should escape HTML in user data."""
        events = [
            {"stage": "<script>alert('xss')</script>", "step_id": 1, "trace_id": "x", "outcome": "ok", "dt": 0},
        ]
        
        html_content = render_html({}, events, tmp_path)
        
        # User-supplied script tag should be escaped (not the legitimate JS in head)
        # The malicious XSS payload should appear escaped in the events table
        assert "&lt;script&gt;alert" in html_content
        assert "&lt;/script&gt;" in html_content


class TestDashboardIntegration:
    """Integration tests for full dashboard generation."""
    
    def test_full_dashboard_generation(self, tmp_path: Path):
        """Should generate complete dashboard file."""
        # Create test data
        summary = {
            "processed": 10,
            "filled": 5,
            "stages_by_name": {"strategy": {"count": 10, "p50_ms": 1.0, "p95_ms": 2.0}},
            "outcomes_by_stage": {"strategy": {"ok": 10}},
            "stage_events_count": 10,
        }
        (tmp_path / "metrics_summary.json").write_text(json.dumps(summary))
        
        events = [{"stage": "test", "step_id": i, "trace_id": f"t{i}", "outcome": "ok", "dt": 0.001} for i in range(5)]
        ndjson = "\n".join(json.dumps(e) for e in events) + "\n"
        (tmp_path / "metrics.ndjson").write_text(ndjson)
        
        # Render
        loaded_summary = load_summary(tmp_path)
        loaded_events = tail_ndjson_files(tmp_path)
        html = render_html(loaded_summary, loaded_events, tmp_path)
        
        # Write and verify
        out_path = tmp_path / "dashboard.html"
        out_path.write_text(html, encoding="utf-8")
        
        assert out_path.exists()
        content = out_path.read_text(encoding="utf-8")
        assert len(content) > 500  # Should have substantial content
        assert "strategy" in content
        assert "5" in content  # events shown


class TestDashboardV1Features:
    """Tests for AG-3I-4-1 Dashboard v1 features."""
    
    def test_generated_at_with_injectable_now_fn(self, tmp_path: Path):
        """Should use now_fn for deterministic timestamp in tests."""
        from datetime import datetime, timezone
        
        fixed_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        html_content = render_html({}, [], tmp_path, now_fn=lambda: fixed_dt)
        
        assert "Generated at:" in html_content
        assert "2026-01-15T12:00:00+00:00" in html_content
    
    def test_run_id_from_summary(self, tmp_path: Path):
        """Should display run_id from summary metadata."""
        summary = {"run_id": "my_custom_run_123"}
        
        html_content = render_html(summary, [], tmp_path)
        
        assert "Run ID:" in html_content
        assert "my_custom_run_123" in html_content
    
    def test_run_id_fallback_to_dir_name(self, tmp_path: Path):
        """Should fall back to run_dir name if run_id not in summary."""
        # tmp_path will have a name like tmpXXXXXX
        html_content = render_html({}, [], tmp_path)
        
        assert "Run ID:" in html_content
        # tmp_path name should be used as fallback
        assert tmp_path.name in html_content
    
    def test_top_stages_section_exists(self, tmp_path: Path):
        """Should contain Top Stages by P95 section."""
        summary = {
            "stages_by_name": {
                "strategy": {"count": 100, "p50_ms": 0.5, "p95_ms": 1.0},
                "risk": {"count": 80, "p50_ms": 0.3, "p95_ms": 2.5},
                "exec": {"count": 50, "p50_ms": 1.0, "p95_ms": 5.0},
            },
        }
        
        html_content = render_html(summary, [], tmp_path)
        
        assert "Top Stages by P95" in html_content
    
    def test_top_stages_sorted_descending(self, tmp_path: Path):
        """Top stages should be sorted by P95 descending."""
        summary = {
            "stages_by_name": {
                "strategy": {"count": 100, "p50_ms": 0.5, "p95_ms": 1.0},    # lowest p95
                "risk": {"count": 80, "p50_ms": 0.3, "p95_ms": 2.5},         # middle
                "exec": {"count": 50, "p50_ms": 1.0, "p95_ms": 5.0},         # highest p95
            },
        }
        
        html_content = render_html(summary, [], tmp_path)
        
        # Find the positions in the HTML to verify order
        exec_pos = html_content.find(">exec<") if ">exec<" in html_content else html_content.find("exec")
        risk_pos = html_content.find(">risk<") if ">risk<" in html_content else html_content.find("risk")
        strategy_pos = html_content.find(">strategy<") if ">strategy<" in html_content else html_content.find("strategy")
        
        # exec (5.0) should appear before risk (2.5) which should appear before strategy (1.0)
        # In the Top Stages section (not the regular Stages section)
        top_stages_start = html_content.find("Top Stages by P95")
        stages_section_start = html_content.find("<!-- Stages Section -->")
        
        # Extract just the Top Stages section
        top_section = html_content[top_stages_start:stages_section_start]
        
        exec_in_top = top_section.find("exec")
        risk_in_top = top_section.find("risk")
        strategy_in_top = top_section.find("strategy")
        
        assert exec_in_top < risk_in_top < strategy_in_top, (
            f"Expected exec < risk < strategy in Top Stages section: "
            f"exec={exec_in_top}, risk={risk_in_top}, strategy={strategy_in_top}"
        )
    
    def test_top_stages_handles_missing_p95(self, tmp_path: Path):
        """Should handle stages with missing p95_ms gracefully."""
        summary = {
            "stages_by_name": {
                "strategy": {"count": 100, "p50_ms": 0.5},  # No p95_ms
                "risk": {"count": 80, "p95_ms": 2.5},       # Has p95_ms
            },
        }
        
        html_content = render_html(summary, [], tmp_path)
        
        # Should not crash, and should contain both stages
        assert "Top Stages by P95" in html_content
        assert "strategy" in html_content
        assert "risk" in html_content
        assert "N/A" in html_content  # strategy should show N/A for p95
    
    def test_js_refresh_script_present(self, tmp_path: Path):
        """Should contain JS for querystring-based refresh."""
        html_content = render_html({}, [], tmp_path)
        
        # Check for refresh-related JS patterns
        assert "URLSearchParams" in html_content
        assert "refresh" in html_content
        assert "refresh-meta" in html_content
        assert "refresh-indicator" in html_content
    
    def test_refresh_indicator_hidden_by_default(self, tmp_path: Path):
        """Refresh indicator should be hidden by default (no ?refresh=N)."""
        html_content = render_html({}, [], tmp_path)
        
        # Check that indicator has display:none by default
        assert 'style="display:none;' in html_content or "style='display:none;" in html_content


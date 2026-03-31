"""Tests for the Metrics class."""
import pytest
from src.api.main import Metrics


def test_metrics_initialization():
    """Test Metrics initializes with correct defaults."""
    m = Metrics()
    assert m.requests_total == 0
    assert m.errors_total == 0
    assert m.latency_count == 0
    assert m.latency_sum_ms == 0.0


def test_record_request():
    """Test recording requests updates counters."""
    m = Metrics()
    m.record_request("/api/chat", 200, 100.0)
    assert m.requests_total == 1
    assert m.requests_by_route["/api/chat"] == 1
    assert m.requests_by_status[200] == 1
    assert m.latency_count == 1
    assert m.latency_sum_ms == 100.0
    assert m.errors_total == 0


def test_record_error():
    """Test recording errors increments error counter."""
    m = Metrics()
    m.record_request("/api/chat", 500, 200.0)
    assert m.errors_total == 1


def test_prometheus_export():
    """Test Prometheus format export."""
    m = Metrics()
    m.record_request("/api/chat", 200, 100.0)
    output = m.to_prometheus()
    assert "agentunity_requests_total 1" in output
    assert "agentunity_requests_by_route" in output
    assert "agentunity_latency_avg_ms" in output
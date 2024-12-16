"""Metrics collection and monitoring for pipes."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class MetricValue(BaseModel):
    """A single metric value with timestamp."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    timestamp: datetime
    value: float


class MetricWindow(BaseModel):
    """A time window of metric values."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    values: List[MetricValue]
    window_size: timedelta

    def add_value(self, value: float) -> None:
        """Add a value to the window."""
        now = datetime.now()
        self.values.append(MetricValue(timestamp=now, value=value))

        # Remove old values
        cutoff = now - self.window_size
        self.values = [v for v in self.values if v.timestamp > cutoff]

    @property
    def average(self) -> Optional[float]:
        """Calculate average value in window."""
        if not self.values:
            return None
        return sum(v.value for v in self.values) / len(self.values)

    @property
    def min(self) -> Optional[float]:
        """Get minimum value in window."""
        if not self.values:
            return None
        return min(v.value for v in self.values)

    @property
    def max(self) -> Optional[float]:
        """Get maximum value in window."""
        if not self.values:
            return None
        return max(v.value for v in self.values)


class MetricsCollector:
    """Collects and aggregates metrics over time windows."""

    def __init__(self, window_size: timedelta = timedelta(minutes=5)) -> None:
        """Initialize metrics collector.

        Args:
            window_size: Time window for metrics aggregation
        """
        self.window_size = window_size
        self.processing_times = MetricWindow(values=[], window_size=window_size)
        self.error_rates = MetricWindow(values=[], window_size=window_size)
        self.throughput = MetricWindow(values=[], window_size=window_size)

    def record_processing_time(self, duration: float) -> None:
        """Record a processing time measurement."""
        self.processing_times.add_value(duration)

    def record_error(self) -> None:
        """Record an error occurrence."""
        self.error_rates.add_value(1.0)

    def record_success(self) -> None:
        """Record a successful processing."""
        self.error_rates.add_value(0.0)

    def record_throughput(self, items: int) -> None:
        """Record throughput measurement."""
        self.throughput.add_value(float(items))

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "processing_time": {
                "avg": self.processing_times.average,
                "min": self.processing_times.min,
                "max": self.processing_times.max,
            },
            "error_rate": {
                "avg": self.error_rates.average,
                "min": self.error_rates.min,
                "max": self.error_rates.max,
            },
            "throughput": {
                "avg": self.throughput.average,
                "min": self.throughput.min,
                "max": self.throughput.max,
            },
        }

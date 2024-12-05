# Monitoring

## Overview

Pipeflow provides comprehensive monitoring capabilities to help you track the performance and health of your data processing pipelines.

## Basic Monitoring

Enable basic monitoring:

```python
from pipeflow.monitoring import PipelineMonitor

# Create monitor
monitor = PipelineMonitor()

# Attach to pipeline
pipeline.set_monitor(monitor)

# Process data
await pipeline.process(data)

# Get metrics
metrics = monitor.get_metrics()
print(f"Total processing time: {metrics.total_time}")
print(f"Records processed: {metrics.record_count}")
```

## Metrics Collection

Available metrics include:

- Processing time
- Record count
- Error rate
- Memory usage
- Throughput
- Latency

```python
from pipeflow.monitoring import MetricsCollector

collector = MetricsCollector()
pipeline.set_metrics_collector(collector)

# Get detailed metrics
metrics = collector.get_metrics()
print(f"Average latency: {metrics.avg_latency}")
print(f"Throughput: {metrics.throughput} records/sec")
```

## Custom Metrics

Add custom metrics:

```python
from pipeflow.monitoring import CustomMetric

class MyMetric(CustomMetric):
    def __init__(self):
        self.value = 0
    
    def update(self, value):
        self.value = value
    
    def get_value(self):
        return self.value

# Use custom metric
metric = MyMetric()
monitor.add_metric("custom", metric)
```

## Prometheus Integration

Export metrics to Prometheus:

```python
from pipeflow.monitoring.exporters import PrometheusExporter

exporter = PrometheusExporter(
    job_name="my_pipeline",
    push_gateway="localhost:9091"
)

monitor.add_exporter(exporter)
```

## Logging

Configure logging:

```python
from pipeflow.monitoring import LogMonitor
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline")

# Create monitor
log_monitor = LogMonitor(logger)
pipeline.set_log_monitor(log_monitor)
```

## Alerting

Set up alerts:

```python
from pipeflow.monitoring import AlertManager

alerts = AlertManager(
    error_threshold=0.01,  # 1% error rate
    latency_threshold=1000,  # 1 second
    throughput_threshold=100  # min records/sec
)

monitor.set_alert_manager(alerts)

# Handle alerts
@alerts.on_alert
def handle_alert(alert):
    print(f"Alert: {alert.message}")
```

## Best Practices

1. Monitor key metrics
2. Set up appropriate alerts
3. Use custom metrics for specific needs
4. Configure proper logging
5. Export metrics to monitoring systems
6. Review metrics regularly

from collections.abc import MutableMapping
from dataclasses import dataclass
import os
from threading import Lock
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span

TRACEPARENT_ENV = "TRACEPARENT"
TRACESTATE_ENV = "TRACESTATE"
_OTEL_TRACE_KEYS = ("traceparent", "tracestate")


@dataclass(frozen=True)
class TelemetryProviders:
    tracer_provider: TracerProvider
    meter_provider: MeterProvider


class PortalTelemetry:
    """Application telemetry instruments with one process-wide provider pair."""

    def __init__(self, providers: TelemetryProviders) -> None:
        self.providers = providers
        self.tracer = providers.tracer_provider.get_tracer("aiconfigurator.portal")
        meter = providers.meter_provider.get_meter("aiconfigurator.portal")

        self.runs_total = meter.create_counter(
            "portal.runs",
            unit="{run}",
            description="Terminal portal runs by status",
        )
        self.active_runs = meter.create_up_down_counter(
            "portal.runs.active",
            unit="{run}",
            description="Currently executing portal runs",
        )
        self.queued_runs = meter.create_up_down_counter(
            "portal.queue.depth",
            unit="{run}",
            description="Currently queued portal runs",
        )
        self.run_duration = meter.create_histogram(
            "portal.run.duration",
            unit="s",
            description="Portal run duration",
        )
        self.subprocess_outcomes = meter.create_counter(
            "portal.subprocess.outcomes",
            unit="{subprocess}",
            description="AIConfigurator subprocess outcomes",
        )
        self.artifact_bytes = meter.create_counter(
            "portal.artifact.bytes",
            unit="By",
            description="Bytes written to completed run artifacts",
        )

    def record_queue_state(
        self,
        span: Span | None,
        *,
        depth: int,
        capacity: int,
        event_name: str,
    ) -> None:
        attributes: dict[str, int | float] = {
            "queue.depth": depth,
            "queue.capacity": capacity,
            "queue.saturation_ratio": depth / capacity,
        }
        if span is not None and span.is_recording():
            span.add_event(event_name, attributes=attributes)
            for name, value in attributes.items():
                span.set_attribute(name, value)

    def record_terminal_run(
        self,
        status: str,
        *,
        duration_ms: int | None,
        active: bool,
    ) -> None:
        self.runs_total.add(1, {"status": status})
        if active:
            self.active_runs.add(-1)
        if duration_ms is not None:
            self.run_duration.record(duration_ms / 1000)

    def record_artifact_bytes(self, total_bytes: int) -> None:
        if total_bytes > 0:
            self.artifact_bytes.add(total_bytes)

    def record_subprocess_outcome(self, outcome: str) -> None:
        self.subprocess_outcomes.add(1, {"outcome": outcome})

    def force_flush(self) -> None:
        self.providers.tracer_provider.force_flush()
        self.providers.meter_provider.force_flush()

    def shutdown(self) -> None:
        self.providers.tracer_provider.shutdown()
        self.providers.meter_provider.shutdown()


_telemetry: PortalTelemetry | None = None
_telemetry_lock = Lock()


def get_telemetry() -> PortalTelemetry:
    global _telemetry
    if _telemetry is not None:
        return _telemetry
    with _telemetry_lock:
        if _telemetry is None:
            _telemetry = _build_telemetry()
    return _telemetry


def _build_telemetry() -> PortalTelemetry:
    resource = Resource.create(
        {
            SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "aiconfigurator-portal")
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    if _signal_uses_otlp("traces"):
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter())
        )
    trace.set_tracer_provider(tracer_provider)

    prometheus_reader = PrometheusMetricReader()
    metric_readers: list[Any] = [prometheus_reader]
    if _signal_uses_otlp("metrics"):
        metric_readers.append(
            PeriodicExportingMetricReader(OTLPMetricExporter())
        )
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)
    return PortalTelemetry(
        TelemetryProviders(
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
        )
    )


def inject_trace_context(environ: MutableMapping[str, str]) -> None:
    """Copy the current W3C trace context into subprocess environment variables."""

    carrier: dict[str, str] = {}
    from opentelemetry import propagate

    propagate.inject(carrier)
    for key in _OTEL_TRACE_KEYS:
        value = carrier.get(key)
        if value:
            environ[key.upper()] = value


def extract_trace_context(environ: MutableMapping[str, str]):
    """Extract W3C trace context from the portal wrapper's environment variables."""

    from opentelemetry import propagate

    carrier = {
        key: environ[env_key]
        for key, env_key in (
            ("traceparent", TRACEPARENT_ENV),
            ("tracestate", TRACESTATE_ENV),
        )
        if environ.get(env_key)
    }
    return propagate.extract(carrier)


def _signal_uses_otlp(signal_name: str) -> bool:
    endpoint = os.getenv(f"OTEL_EXPORTER_OTLP_{signal_name.upper()}_ENDPOINT")
    base_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    exporters = os.getenv(f"OTEL_{signal_name.upper()}_EXPORTER", "")
    return bool(
        endpoint
        or base_endpoint
        or "otlp" in {value.strip().lower() for value in exporters.split(",")}
    )

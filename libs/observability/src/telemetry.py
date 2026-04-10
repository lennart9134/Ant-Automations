"""Unified telemetry setup for all Ant Automations services.

Configures OpenTelemetry tracing and metrics with OTLP gRPC export.
Each service calls configure_telemetry(service_name) at startup.
"""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


def configure_telemetry(
    service_name: str,
    otlp_endpoint: str = "http://otel-collector:4317",
) -> TracerProvider:
    """Initialize OpenTelemetry tracing for a service.

    Args:
        service_name: Identifies the service in traces (e.g., "planner", "connectors").
        otlp_endpoint: OTLP gRPC collector endpoint.

    Returns:
        Configured TracerProvider.
    """
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    return provider

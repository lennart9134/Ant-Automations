"""Platform-wide metrics definitions.

14 pre-defined metrics covering workflows, steps, connectors, model inference,
and approval latency. All services use AntMetrics for consistent metric naming.
"""

from opentelemetry import metrics


class AntMetrics:
    """Centralized metric instruments for the Ant Automations platform."""

    def __init__(self, meter_name: str = "ant_automations") -> None:
        meter = metrics.get_meter(meter_name)

        # Workflow metrics
        self.workflow_total = meter.create_counter(
            "ant.workflow.total",
            description="Total workflow executions",
        )
        self.workflow_success = meter.create_counter(
            "ant.workflow.success",
            description="Successful workflow completions",
        )
        self.workflow_failed = meter.create_counter(
            "ant.workflow.failed",
            description="Failed workflow executions",
        )
        self.workflow_duration = meter.create_histogram(
            "ant.workflow.duration_ms",
            description="Workflow execution duration in milliseconds",
            unit="ms",
        )

        # Step metrics
        self.step_total = meter.create_counter(
            "ant.step.total",
            description="Total workflow step executions",
        )
        self.step_duration = meter.create_histogram(
            "ant.step.duration_ms",
            description="Step execution duration in milliseconds",
            unit="ms",
        )

        # Connector metrics
        self.connector_calls = meter.create_counter(
            "ant.connector.calls",
            description="Total connector action calls",
        )
        self.connector_errors = meter.create_counter(
            "ant.connector.errors",
            description="Connector action errors",
        )
        self.connector_latency = meter.create_histogram(
            "ant.connector.latency_ms",
            description="Connector action latency in milliseconds",
            unit="ms",
        )

        # Model inference metrics
        self.model_calls = meter.create_counter(
            "ant.model.calls",
            description="Total model inference calls",
        )
        self.model_latency = meter.create_histogram(
            "ant.model.latency_ms",
            description="Model inference latency in milliseconds",
            unit="ms",
        )
        self.model_tokens = meter.create_counter(
            "ant.model.tokens",
            description="Total tokens processed by models",
        )

        # Approval metrics
        self.approval_requests = meter.create_counter(
            "ant.approval.requests",
            description="Total approval requests created",
        )
        self.approval_latency = meter.create_histogram(
            "ant.approval.latency_ms",
            description="Time from approval request to decision in milliseconds",
            unit="ms",
        )

"""
Arize Phoenix Observability Setup

Configures Phoenix for LLM observability, tracing, and monitoring.
"""

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from nexusflow.config import settings

logger = structlog.get_logger(__name__)

_tracer: trace.Tracer | None = None
_initialized = False


def setup_phoenix() -> None:
    """
    Initialize Arize Phoenix for observability.

    This sets up:
    - OpenTelemetry tracing with Phoenix exporter
    - LangChain instrumentation
    - Custom spans for classification pipeline
    """
    global _initialized

    if _initialized:
        logger.debug("Phoenix already initialized")
        return

    if not settings.phoenix_enabled:
        logger.info("Phoenix observability disabled")
        return

    try:
        # Create resource with service name
        resource = Resource.create(
            {
                SERVICE_NAME: settings.phoenix_project_name,
                "service.version": settings.app_version,
                "deployment.environment": settings.environment,
            }
        )

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter for Phoenix
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.phoenix_grpc_endpoint,
            insecure=True,  # For local development
        )

        # Add span processor
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Set as global tracer provider
        trace.set_tracer_provider(provider)

        # Instrument LangChain (if available)
        try:
            from openinference.instrumentation.langchain import LangChainInstrumentor

            LangChainInstrumentor().instrument()
            logger.info("LangChain instrumentation enabled")
        except ImportError:
            logger.debug("LangChain instrumentation not available")

        _initialized = True
        logger.info(
            "Phoenix observability initialized",
            endpoint=settings.phoenix_grpc_endpoint,
            project=settings.phoenix_project_name,
        )

    except Exception as e:
        logger.error("Failed to initialize Phoenix", error=str(e))


def get_tracer(name: str = "nexusflow") -> trace.Tracer:
    """
    Get a tracer for creating custom spans.

    Usage:
        tracer = get_tracer()
        with tracer.start_as_current_span("my_operation") as span:
            span.set_attribute("custom.attribute", "value")
            # ... do work ...
    """
    global _tracer

    if _tracer is None:
        _tracer = trace.get_tracer(name, settings.app_version)

    return _tracer


def trace_classification(func):
    """
    Decorator to trace classification operations.

    Usage:
        @trace_classification
        async def classify_ticket(ticket):
            ...
    """
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tracer = get_tracer()

        with tracer.start_as_current_span(
            f"classification.{func.__name__}",
            kind=trace.SpanKind.INTERNAL,
        ) as span:
            # Add input attributes
            if kwargs.get("ticket_id"):
                span.set_attribute("ticket.id", str(kwargs["ticket_id"]))
            if kwargs.get("title"):
                span.set_attribute("ticket.title", kwargs["title"][:100])

            try:
                result = await func(*args, **kwargs)

                # Add result attributes
                if isinstance(result, dict):
                    if "classification" in result:
                        cls = result["classification"]
                        span.set_attribute("classification.level1", cls.get("level1", ""))
                        span.set_attribute("classification.level2", cls.get("level2", ""))
                        span.set_attribute("classification.level3", cls.get("level3", ""))
                    if "confidence" in result:
                        conf = result["confidence"]
                        span.set_attribute("confidence.calibrated", conf.get("calibrated_score", 0))
                        span.set_attribute(
                            "confidence.agreement", conf.get("component_agreement", 0)
                        )
                    if "routing" in result:
                        span.set_attribute(
                            "routing.requires_hitl", result["routing"].get("requires_hitl", False)
                        )

                span.set_status(trace.Status(trace.StatusCode.OK))
                return result

            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    return wrapper


def trace_graph_query(func):
    """Decorator to trace graph database queries."""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tracer = get_tracer()

        with tracer.start_as_current_span(
            f"neo4j.{func.__name__}",
            kind=trace.SpanKind.CLIENT,
        ) as span:
            span.set_attribute("db.system", "neo4j")
            span.set_attribute("db.operation", func.__name__)

            try:
                result = await func(*args, **kwargs)
                span.set_status(trace.Status(trace.StatusCode.OK))

                # Record result count if applicable
                if isinstance(result, list):
                    span.set_attribute("db.result_count", len(result))

                return result
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    return wrapper


def trace_vector_search(func):
    """Decorator to trace vector database searches."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracer = get_tracer()

        with tracer.start_as_current_span(
            f"milvus.{func.__name__}",
            kind=trace.SpanKind.CLIENT,
        ) as span:
            span.set_attribute("db.system", "milvus")
            span.set_attribute("db.operation", func.__name__)

            if kwargs.get("limit"):
                span.set_attribute("search.limit", kwargs["limit"])

            try:
                result = func(*args, **kwargs)
                span.set_status(trace.Status(trace.StatusCode.OK))

                if isinstance(result, list):
                    span.set_attribute("search.result_count", len(result))

                return result
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    return wrapper


def trace_llm_call(func):
    """Decorator to trace LLM API calls."""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tracer = get_tracer()

        with tracer.start_as_current_span(
            f"llm.{func.__name__}",
            kind=trace.SpanKind.CLIENT,
        ) as span:
            span.set_attribute("llm.provider", "azure_openai")
            span.set_attribute("llm.model", settings.azure_openai_deployment_name)

            try:
                result = await func(*args, **kwargs)
                span.set_status(trace.Status(trace.StatusCode.OK))
                return result
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    return wrapper


class ClassificationSpan:
    """
    Context manager for creating detailed classification spans.

    Usage:
        async with ClassificationSpan(ticket_id="123", title="Test") as span:
            span.set_graph_result(paths, confidence)
            span.set_vector_result(matches, confidence)
            span.set_llm_result(prediction, confidence)
            span.set_final_result(classification, ensemble_confidence)
    """

    def __init__(
        self,
        ticket_id: str,
        title: str,
        description: str = None,
    ):
        self.ticket_id = ticket_id
        self.title = title
        self.description = description
        self._tracer = get_tracer()
        self._span = None

    async def __aenter__(self):
        self._span = self._tracer.start_span(
            "classification.pipeline",
            kind=trace.SpanKind.INTERNAL,
        )

        self._span.set_attribute("ticket.id", self.ticket_id)
        self._span.set_attribute("ticket.title", self.title[:100])
        if self.description:
            self._span.set_attribute("ticket.description_length", len(self.description))

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
            self._span.record_exception(exc_val)
        else:
            self._span.set_status(trace.Status(trace.StatusCode.OK))

        self._span.end()

    def set_graph_result(self, paths: list, confidence: float):
        """Record graph query results."""
        self._span.set_attribute("graph.path_count", len(paths))
        self._span.set_attribute("graph.confidence", confidence)

    def set_vector_result(self, matches: list, confidence: float):
        """Record vector search results."""
        self._span.set_attribute("vector.match_count", len(matches))
        self._span.set_attribute("vector.confidence", confidence)

    def set_llm_result(self, prediction: dict, confidence: float):
        """Record LLM judgment results."""
        self._span.set_attribute("llm.confidence", confidence)
        if prediction:
            self._span.set_attribute("llm.level1", prediction.get("level1", ""))

    def set_final_result(
        self,
        classification: dict,
        confidence: float,
        requires_hitl: bool,
    ):
        """Record final classification result."""
        self._span.set_attribute("result.level1", classification.get("level1", ""))
        self._span.set_attribute("result.level2", classification.get("level2", ""))
        self._span.set_attribute("result.level3", classification.get("level3", ""))
        self._span.set_attribute("result.confidence", confidence)
        self._span.set_attribute("result.requires_hitl", requires_hitl)

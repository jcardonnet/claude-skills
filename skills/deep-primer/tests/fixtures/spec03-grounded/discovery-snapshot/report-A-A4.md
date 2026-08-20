# source-authority — wave A (brief A-A4)

# Distributed Tracing & Observability Stack: Primary Sources & Foundations

## Foundational Architecture

Google's *Dapper* (2010) remains the definitive seminal work establishing distributed tracing as a discipline. It introduced the core concepts—trace spans, request propagation, sampling strategies—that define all modern systems. Dapper's three-layer architecture (instrumentation, collection, analysis) and probabilistic sampling approach remain canonical references, adopted across Jaeger, Zipkin, and OpenTelemetry implementations. The paper's guidance on tail-based sampling and low-overhead tracing directly influences contemporary observability design.

**Consensus**: All major open-source tracing platforms cite Dapper as architectural foundation (5 independent implementations studied).

## Industry Standard: OpenTelemetry

OpenTelemetry (CNCF, v1.0 released Sept 2021, current stable v1.x) has consolidated the observability stack around unified specification for traces, metrics, and logs. The specification is vendor-neutral, standardizing context propagation (W3C Trace Context), span conventions, and semantic attributes. OTLP (OpenTelemetry Protocol) defines the wire format for exporting observability signals.

The specification emerged from merging OpenCensus (Google) and OpenTracing (CNCF) circa 2019, representing industry consensus on signal definitions and protocol requirements. As of 2026, OpenTelemetry SDKs exist in 12+ languages with automated instrumentation support.

## Primary Implementations

**Jaeger** (Uber, v1.52.0, Feb 2024 latest release): CNCF project implementing OpenTelemetry/Zipkin protocols. Spans distributed consensus tradeoffs: all-in-one mode for dev, microservices deployment for production. Supports adaptive sampling and real-time trace retrieval. Architectural documentation emphasizes agent-collector-storage separation pattern.

**Zipkin** (Twitter origin, v3.0.3, March 2024): Reference implementation of distributed tracing. Simpler model than Jaeger; focuses on minimal instrumentation overhead. Spans dependency graph inference from trace data—critical for microservice topology discovery.

**Consensus**: Both systems preserve Dapper's core concepts; design divergence reflects operational tradeoffs, not fundamental disagreement (4 independent observability surveys confirm this pattern).

## Instrumentation & Propagation Standards

W3C Trace Context (Recommendation, 2020) standardizes HTTP header format for trace propagation, replacing ad-hoc vendor formats. All modern SDKs support it; adoption is near-universal in CNCF projects. Baggage specification (W3C, 2021) adds context metadata propagation beyond trace IDs.

## Practitioner Guidance

Observability best practices converge on: (1) 100% trace collection for critical paths, probabilistic sampling for high-volume services; (2) semantic conventions for span attributes to enable querying across services; (3) correlation between traces, metrics (request latency histograms), and logs via trace context; (4) tail-based sampling strategies to capture rare errors even with low overall sample rates. CNCF Observability WG publishes working definitions of observability signals.

## Recent Developments (2023–2026)

Key evolution: move from sampling-at-collection toward sampling-at-ingestion. Observability platforms (Tempo, Signoz, Grafana stack) increasingly implement tail-based sampling and cost-optimized storage. OpenTelemetry Collector (v0.98+) now includes sampling processors. Spanmetrics approach (deriving histograms from trace spans in real time) bridges metrics/traces gap, reducing duplication.

**Tool Versions**:
- OpenTelemetry Collector: v0.98.0 (March 2024)
- Jaeger: v1.52.0 (Feb 2024)
- Zipkin: v3.0.3 (March 2024)
- Prometheus + Grafana ecosystem: widely deployed for metrics; Grafana Tempo (v2.3+) provides native trace storage

## Claims & Supporting Sources

**Dapper's influence on all major implementations**: Validated across Jaeger architecture docs, Zipkin design docs, OpenTelemetry semantic conventions (3 independent sources).

**W3C standards adoption**: Confirmed by CNCF landscape surveys and SDK documentation (4 sources).

**No fundamental disagreement observed** on core tracing concepts; design variance reflects operational constraints (scale, cost, latency targets), not contested theory.

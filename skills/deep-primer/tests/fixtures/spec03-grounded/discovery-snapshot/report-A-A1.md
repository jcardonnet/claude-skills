# structure — wave A (brief A-A1)

# Distributed Tracing & Observability Landscape

## Canonical Architecture

OpenTelemetry (OTel) defines the canonical taxonomy for observability, organizing systems into **signals**—independent telemetry categories that share context propagation. These include: **Traces** (request paths across services), **Metrics** (time-series measurements), **Logs** (timestamped events), **Profiles** (CPU/memory consumption), and **Baggage** (in-band context key-value pairs). Signals function independently with no ordering requirements; correlation occurs via execution context (TraceId, SpanId, resource metadata, and timestamp).

## Layered Stack Architecture

Practitioners organize observability into seven distinct layers:

**1. Instrumentation Layer:** Manual SDK integration (OpenTelemetry SDKs across 15+ languages), auto-instrumentation (language-specific agents or eBPF), and zero-code eBPF instrumentation capturing spans without code changes.

**2. Collection Layer:** OpenTelemetry Collector (vendor-neutral hub accepting 50+ receiver types, applying processors, exporting to backends), language-specific sidecar agents, and direct application exports.

**3. Context Propagation Layer:** W3C Trace Context (HTTP header standard), B3 Propagation (Zipkin legacy format), and vendor formats (Datadog, Jaeger). Multiple propagators coexist in heterogeneous systems via extraction/injection multiplexing.

**4. Storage Layer:** Purpose-built backends—Jaeger (distributed tracing), Prometheus (metrics), Loki (logs via label indexing), ELK Stack, and vendor platforms (Datadog, Splunk, New Relic).

**5. Visualization Layer:** Grafana (multi-signal dashboards, 11.2.2), Jaeger UI (trace exploration), OpenSearch Dashboards, and vendor UIs.

**6. Analysis Layer:** Service mesh observability (Istio provides transparent instrumentation), APM platforms offering correlation, alerting, and anomaly detection.

## Method Families by Implementation Strategy

### By Sampling Approach
- **Head sampling:** Decisions at ingestion (Jaeger probabilistic: random 0–100%, or rate-limiting: fixed throughput). Remote sampling allows centralized policy via Jaeger sampling.proto.
- **Tail sampling:** Decisions post-collection, enabling high-cardinality span filtering (rare-event capture).

### By Instrumentation Strategy
- **Manual instrumentation:** Explicit SDK calls for full control; highest fidelity, requires code changes.
- **Auto-instrumentation:** Language-specific agents (Go instrumentation via eBPF, PHP zend_observer hooks, OpenTelemetry eBPF for Linux binaries) reduce developer burden.
- **Zero-code eBPF:** Kernel-space probes capture traces from binaries without recompilation.

### By Vendor Strategy
- **Vendor-agnostic (OpenTelemetry):** Portable SDKs, pluggable exporters, multi-vendor support.
- **Vendor-specific (Datadog, Splunk):** Proprietary APIs with platform integration; lock-in vs native feature depth trade-off.
- **Open-source backend:** Jaeger + Prometheus + Loki (2.20, latest, 3.7.0 respectively) allow self-hosting; operational burden vs cost savings.

### By Deployment Pattern
- **Sidecar collectors:** Per-pod OpenTelemetry Collector (via Kubernetes operator) centralizes processing.
- **Centralized collector:** Shared infrastructure for cost efficiency and cross-service policies.
- **Direct export:** Applications bypass collectors, increasing network overhead but simplifying topology.

## Disciplinary Subfields

**Distributed Tracing (Core):** Spans with parent-child relationships, latency analysis, critical path identification. Standards: OpenTelemetry, W3C Trace Context, B3, OpenTracing (legacy).

**Application Performance Monitoring (APM):** Correlating traces with metrics and profiles; baselines and anomaly detection. Vendor platforms (Datadog, New Relic, Splunk) dominate; OSS via Grafana+Jaeger achieves 70% parity.

**Service Mesh Observability:** Transparent instrumentation at network layer (Istio generates client/server spans) without SDK changes; L7 protocol introspection.

**Continuous Profiling:** On-demand CPU, memory, and goroutine profiling (pprof format). Emerging signal in OTel; Datadog and Splunk offer production profiling.

**Logs-Traces Correlation:** LogRecords include TraceId/SpanId for bidirectional navigation. Log aggregation (Loki, ELK) indexes label sets for cardinality control.

**Metrics-Traces Correlation:** Exemplars (stable in OTel) attach trace_id/span_id to histogram/gauge observations, enabling drill-down from metric anomalies to traces.

## Practitioner Taxonomy

Organizations carve the landscape into functional roles:

1. **Frontend instrumentation:** Web SDKs (OpenTelemetry JS), browser timing APIs.
2. **Backend instrumentation:** Language SDKs (Java, Python, Go, .NET), Kubernetes downward API for resource context.
3. **Infrastructure observability:** Container/VM metrics, kernel probes (eBPF agents).
4. **Data pipeline:** Collector configuration, sampling policies, retention, cost optimization (trace volume reduction via tail sampling).
5. **Backend operations:** Storage scaling, query optimization, alerting rules.
6. **Analytics:** Root-cause correlation, SLO tracking, capacity planning.

## Key Agreements & Disagreements

**Consensus** (3+ primary sources): OpenTelemetry as lingua franca; Jaeger v2.20 for tracing backends; context propagation via TraceId/SpanId; collector hub pattern for multi-backend support.

**Tension:** Tail sampling adds latency (deferred decisions) vs head sampling loses tail events; vendor-agnostic OTel SDKs miss platform-specific features (Datadog profiling, Splunk ITSI) — practitioners choose portability or depth.

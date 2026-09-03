# contrarian-seed — wave C (brief C-C-disconfirm)

# Distributed Tracing Claims Under Fire: Evidence of Overstatement

## Claim 1: Negligible Overhead
**Verdict: Contradicted by measurement**

Distributed tracing industry literature claims "negligible overhead," but peer-reviewed research shows:
- Throughput reductions of 19-80% depending on workload and span density
- Typical overhead 1-5%, but rising to 10-15% on high-throughput paths
- Storage cost at Alibaba scale: 7,639 GB/day (~$114.6k/month)
- Network overhead up to 102 MB/min between nodes for trace export

The gap: Vendors quote baseline overhead on empty systems; real applications with dense instrumentation incur compounding costs from span serialization, context propagation, and export pipeline processing.

## Claim 2: Sampling Preserves Metric Accuracy
**Verdict: Fundamentally flawed**

With 10% uniform sampling:
- Request/error counts off by 90%
- Duration histograms dramatically underestimated
- Tail latencies—the slowest requests—have low probability of capture

Head-based sampling misses slow paths (decision made before execution). Tail-based sampling requires buffering all in-flight spans in memory, raising host resource overhead. No sampling strategy avoids data loss without revisiting the overhead problem.

## Claim 3: Complete Observability via Tracing
**Verdict: Evidence horizon blindness**

Critical gap: Distributed tracing is instrumented at the application layer and cannot observe infrastructure-level events. A microservice experiencing latency due to:
- Node memory pressure
- OOMKill events
- Kernel page faults
- Network buffer exhaustion

All manifest as symptoms in application traces, but root cause remains invisible. Tracing operates above the container runtime boundary, creating false confidence in observability completeness. This is the highest-impact failure mode: diagnosis appears complete while causal chain remains opaque.

## Failure Mode 1: Cardinality Explosion
**Why it matters: Real, uncontrolled**

Including unique identifiers (request IDs, UUIDs, timestamps) in span names or high-cardinality attributes causes:
- Index collapse under dimensionality
- Storage expansion beyond budgeted capacity
- Query performance degradation to unusable latencies
- Unintended at instrumentation time; discovered in production at scale

This is the most common operational failure in OpenTelemetry implementations. Prevention requires institutional discipline across all instrumentation points.

## Failure Mode 2: Sampling Bias Blindness
- Uniform sampling: Overlapping normal traces, missing edge cases and error bursts
- Tail-based sampling: Retains 80%+ abnormal traces, negligible normal traces → frequent query misses for baseline behavior
- Adaptive sampling: Complex to implement, rarely tuned correctly

## Failure Mode 3: Instrumentation and Integration Burden
**Severity: Underestimated in primer literature**

Manual instrumentation across hundreds of microservices in different languages is "a major engineering burden." Requires:
- Coordination across multiple teams for consistency
- Custom header forwarding in data plane (breaks if missed)
- Configuration complexity that grows exponentially with scale
- Trace exploration remains difficult despite data collection—analyzing gigabytes of spans is not automated

## Contradictory Evidence: When Simpler Won
- **Unified observability**: Metrics (fast) detect problems → logs (detailed) provide context → traces (expensive) show path only when needed
- **Metrics-first**: Accurate metrics outperform sampled tracing for SLO validation
- **Edge processing**: OpenTelemetry Collector-side sampling controls volume more efficiently than application-level instrumentation
- **Alternative sampling policies**: Keeping all errors, sampling above latency thresholds, and probabilistic sampling of normal cases outperform uniform strategies

## Tool Status (August 2026)
- **Jaeger v2** (Nov 2024): Built on OpenTelemetry Collector; v1 EOL'd Dec 31, 2025
- **OpenTelemetry**: Declarative config stable; industry consensus is open-source stack (Prometheus + Grafana + OTEL + Jaeger + Loki) covers 80-90% of commercial APM by 2026
- **Datadog APM**: Still leads enterprise but now seamlessly integrated with OpenTelemetry

## The Contrarian Takeaway
Distributed tracing solves *specific* problems (service-to-service latency attribution, transaction flow visualization) but is **oversold as a complete observability solution**. Primers omit:
1. Real overhead in production (5-15% on dense instrumentation)
2. Sampling's fundamental inability to preserve tail behavior
3. Infrastructure-level visibility gaps (the evidence horizon problem)
4. Cardinality management as a persistent operational burden
5. Manual instrumentation burden across polyglot systems

For most systems, a metrics-first approach with targeted tracing for investigation yields better ROI than comprehensive tracing. The cost-benefit curve breaks down badly beyond moderate scale.

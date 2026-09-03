# debates — wave A (brief A-A2)

# Distributed Tracing Controversies: Open Problems in Observability

Distributed tracing has coalesced around OpenTelemetry as the vendor-neutral standard, yet significant controversies persist on sampling strategies, context propagation interoperability, cardinality management, backend architecture, and span semantics.

## Resolved Consensus (2+ sources)

**Sampling Thresholds**: OTEP 235 resolved the "power-of-two vs. flexible" debate by adopting 56-bit rejection thresholds in W3C Trace Context Level 2, enabling arbitrary probabilities (1%, 10%, 75%) instead of powers of two.

**Context Propagation Standard**: W3C Trace Context adopted as the standard two-header format (`traceparent` + `tracestate`). OpenTelemetry maintains backward compatibility through B3 and Jaeger propagators but defaults to W3C.

## Unresolved Open Problems (8 major)

**1. Tail Sampling Memory vs. Completeness** — The `decision_wait` parameter forces operators to choose: too short = incomplete slow traces with delayed retry spans; too long = unbounded memory growth (20 MB+ per second at typical volumes). GitHub issues #36291, #17275 document real user cases with exponential backoff retries becoming orphaned. Proposed solutions (dynamic trace completion detection, conditional late sampling) remain unimplemented. Disk-based buffering (Pebble) offers partial mitigation but increases latency. **(2 independent sources: Elastic Labs, Michal Drozd)**

**2. Cardinality Explosion as DoS Vector** — 336,000+ Prometheus servers vulnerable to label-injection attacks. Kubernetes with N microservices and M labels generates 2.1+ billion attribute combinations via Cartesian product. OpenTelemetry default cardinality limit of 2000 per metric exists, but GitHub issue #2775 remains unresolved: should Resource attributes be partitioned by signal type (trace vs. metric vs. log) to avoid high-cardinality churn on metric identity? Discussion #3554 asks whether backends should optimize only predefined attributes or support arbitrary searching—no substantive response. **(3 independent sources: Aquasec, Prometheus hardening docs, OpenTelemetry spec)**

**3. Cost Spike Paradox** — Tail-based sampling paradoxically increases data volume during incidents. When network congestion triggers latency, more traces cross latency thresholds, amplifying costs when monitoring is most needed. No consensus algorithm distinguishes "incident latency requiring capture" from "spike requiring suppression." **(2 sources: Cribl, OneUptime)**

**4. Span Semantics Fragmentation** — GitHub issue #1315 seeks to allow INTERNAL span kind for database and LLM operations instead of requiring CLIENT. Current spec recommends CLIENT but permits INTERNAL flexibility, creating de facto inconsistency across implementations (some treat LLM calls as CLIENT, others as INTERNAL). **(1 source: semantic-conventions repo)**

**5. Semantic Conventions Versioning Hell** — Incubating conventions NOT subject to semantic versioning restrictions, allowing breaking changes in minor releases. Language implementations diverge: Python uses internal `_incubating` module; Java splits stable and incubating artifacts; Ruby uses Incubating prefix. GitHub #1168 documents version conflicts when updating a single instrumented library; no resolution on whether incubating should be runtime-safe or copy-pasted. **(2 independent sources: opentelemetry-python-contrib, language-specific repos)**

**6. Backend Architecture Divide** — Jaeger (modular, Go-based, scalable, complex) vs. Zipkin (unified single-process, Java, simple, limited). No consensus on which design philosophy is correct. Tradeoff unresolved: simplicity for PoCs vs. scalability for large systems. OpenTelemetry portability (instrument once, swap backends) helps but backend differences in query language, performance, and features create de facto switching friction. **(3 sources: Last9, Jaeger at 10, SigNoz)**

**7. Context Propagation Complexity** — B3 legacy format requires multi-step migration without breaking backward compatibility. JMS header restrictions forced B3 evolution; semantic differences persist (64-bit vs. 128-bit trace IDs, sampling state ambiguity between "not sampled," "no decision," "debug"). GitHub #7457 documents ongoing migration friction. **(3 sources: B3 RATIONALE, W3C Trace Context, OpenTelemetry Java instrumentation)**

**8. Head-Based vs. Tail-Based Sampling Tradeoff** — Head-based samplers (probabilistic, deterministic) sacrifice visibility into rare events and tail latencies but avoid memory costs. Tail-based offers best signal but worst efficiency. OTEP 250 (compositional samplers) and OTEP 240 (YAML config) in review but unclear status. No consensus on optimal composition. **(2 sources: OneUptime, Cribl)**

## Key Insight

OpenTelemetry successfully standardized **instrumentation** but standardization of **backend behavior, cost models, and operational tradeoffs** remains incomplete. No single "best practice" exists on sampling, cardinality limits, or span semantics.

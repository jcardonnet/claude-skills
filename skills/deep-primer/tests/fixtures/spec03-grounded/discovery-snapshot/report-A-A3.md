# recency-frontier — wave A (brief A-A3)

# Distributed Tracing & Observability Stack: Aug 2025–2026 SOTA

## Major Breaking Changes Reshaping Core SDKs

The past 12 months have seen intentional breaking changes across foundational OpenTelemetry SDKs, signaling a shift toward API stability and deprecation of legacy patterns.

**OpenTelemetry Go v1.45.0** (Aug 3, 2025) restructured the Log API and altered OTLP HTTP endpoint behavior: URLs with no path component now use `/` instead of appending default signal paths (`/v1/metrics`, `/v1/traces`). **OpenTelemetry Java v1.65.0** (Aug 7, 2025) completed removal of the Zipkin exporter and deprecated its OpenCensus shim layer. **OpenTelemetry Collector v1.65.0** (Aug 17, 2025) refactored extended type configurations from embedded to named fields, and **Collector Contrib v0.159.0** removed the Kafka Topics Observer extension after a 3-month deprecation window.

## Legacy Technology End-of-Life

Two predecessor tracing frameworks are now officially archived. **OpenCensus** (archived July 31, 2023) and **OpenTracing** have been fully merged into OpenTelemetry; both ecosystems remain available but unmaintained. The deprecation of OpenCensus and OpenTracing compatibility shims in OpenTelemetry 2026 signals the end of the bridge period—users are expected to migrate directly to native OpenTelemetry instrumentation (3 independent confirmations across OTEL Java, specs, and blog announcements).

**Jaeger Propagator** in OpenTelemetry JavaScript SDK v2.10.0 (July 21, 2025) is marked for removal in SDK 3.x (~September 2026); migration to W3CTraceContextPropagator is recommended. The Jaeger Agent itself has been implicitly superseded by the OpenTelemetry Collector's gRPC receiver pattern, which is now the recommended deployment architecture for new systems.

## Backend Projects: Architectural Maturation

**Jaeger v2.20.0** (July 20, 2026) dropped Elasticsearch v6 support and introduced native trace summaries, marking a shift toward lighter-weight search patterns. **Jaeger v2.19.0** (June 3, 2026) introduced the `/api/v3/trace-summaries` endpoint, representing a structural change in how the UI queries trace data—from full trace retrieval to summary-based search results (2 independent release sources confirm this architectural pattern).

**Grafana Tempo v3.0.3** (Aug 13, 2025) focused on security hardening: updated Go to 1.26.5, gRPC to v1.82.1, and patched CVEs in networking and text libraries. **SigNoz v0.138.0** (Aug 19, 2025) introduced semantic convention name resolution in trace queries and dashboard override editing; notably, v0.137.0 deprecated V1 dashboard APIs in favor of V2.

## New Instrumentation Patterns & Ecosystem Expansion

OpenTelemetry significantly expanded instrumentation capabilities. **eBPF-based instrumentation** shipped an initial release for Go (beta status) and a broader eBPF instrumentation tooling suite, enabling observability without code changes. **Go compile-time instrumentation v1.0** was released, providing another alternative to runtime instrumentation. A new **Kotlin SDK v0.6.0** (July 28, 2025) entered development status for multiplatform support.

**Declarative configuration reached stable status** in 2026, moving configuration-as-code from experimental to production-ready. **OpenTelemetry Profiles entered public alpha** (2026), offering early-stage profiling capabilities. **OTLP with Apache Arrow (Phase 2)** advanced the protocol for efficient telemetry pipelines beyond just transport efficiency.

## Standards Maturation & Semantic Conventions

OpenTelemetry achieved **CNCF graduated project status** in 2026—a milestone confirming production-readiness across core components. **W3C Trace Context** and **OTLP** remain stable; semantic conventions evolved significantly with Kubernetes attributes reaching release-candidate status and CPU metrics transitioning from `.cpu.utilization` to `.cpu.usage`. **Baggage specification** is stable across implementations.

## Shift in Observability Architecture

The ecosystem shows a clear architectural preference: **collector-first patterns** (data flowing through OpenTelemetry Collector for batching, transformation, and filtering) are now recommended at scale, though direct-to-backend remains valid for exploration. **Tail-based sampling** adoption is growing in collector deployments as an alternative to head-based sampling decisions made at instrumentation time. These patterns reflect maturation from quick proof-of-concept setups to production observability infrastructure.

## Summary: From Legacy Cleanup to Production Hardening

The 12-month period (Aug 2025–Aug 2026) is characterized by three themes: (1) removal of legacy compatibility layers and vendor-specific exporters (Zipkin, Jaeger propagators, OpenCensus/OpenTracing shims); (2) hardening of core SDKs through breaking changes that enforce better patterns; and (3) expansion into new instrumentation modalities (eBPF, compile-time) and language support (Kotlin). The ecosystem is consolidating around OTLP, declarative configuration, and collector-centric architectures, with OpenTelemetry's CNCF graduation signaling vendor-neutral observability has reached production maturity.

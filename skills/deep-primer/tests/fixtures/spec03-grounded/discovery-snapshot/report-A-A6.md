# contrarian-seed — wave A (brief A-A6)

# Against Distributed Tracing: The Contrarian Case

## The Performance Paradox

The dominant observability narrative assumes comprehensive distributed tracing is essential for understanding distributed systems. Skeptics argue this imposes severe costs that outweigh benefits. OpenTelemetry instrumentation introduces **7-42% CPU overhead** with **up to 42% latency increases**, depending on configuration (4 independent sources). Selective instrumentation can reduce this by 50-70%, but this defeats the purpose of "comprehensive" tracing. Automatic instrumentation carries approximately twice the overhead of manual approaches—the convenience comes at a steep price.

## The Sampling Trap

All mature tracing systems resort to sampling to manage costs, creating an inescapable trade-off. **Head-based sampling (sampling decisions at request entry) discards unknown outliers upfront**, making it statistically likely that the most important anomalies—tail latencies, rare errors—are permanently lost (5+ independent sources). Tail-based sampling avoids this but increases memory load on tracing infrastructure, requiring retention of all span data until decision points complete. Teams report choosing between missing critical signals or overwhelming storage costs; neither option is acceptable.

## Cost-Benefit Collapse

Industry data shows **97% of organizations experience observability cost surprises**, with 67% reporting they occur regularly. Charity Majors, CTO at Honeycomb (the leading observability vendor for traces), has argued publicly that observability 1.0 (metrics, logs, traces as separate systems) is fundamentally broken—costs rise orders of magnitude faster than traffic, while value delivery decouples from spending. The market has inverted: engineering teams now list cost as their top observability concern. ROI claims of 219-285% assume effective use, but most teams struggle to extract actionable insights from trace data.

## Context Propagation: A Distributed Problem

W3C Trace Context propagation adds 1-5% overhead in typical workloads, scaling to 10-15% on high-throughput paths. Baggage (key-value metadata propagated across requests) introduces variable overhead as tracing context balloons across service boundaries. **Trace context propagation is cited as a frequent failure point** in real systems—context must be threaded flawlessly across every service, protocol, and middleware, making this a distributed coordination problem in itself. Failures are silent: incomplete traces corrupt conclusions.

## The Viable Alternative: Continuous Profiling

Continuous profiling (via tools like Parca, Polar Signals, Pyroscope) offers an alternative signal: **where each service spends CPU/memory over time**, with eBPF-based collection reducing overhead substantially below tracing. Profiling directly answers the debug question "why is this slow?" without request-level correlation. Combined with logs and metrics, it often provides equivalent debugging power at lower cost and complexity. This is not a replacement, but evidence that comprehensive tracing is not the only path to observability.

## Evidence Gaps

While observability vendors claim strong ROI, skeptics note these are benchmarked on well-instrumented customers with dedicated observability teams—survivorship bias. Open-source projects, small teams, and cost-conscious organizations often achieve equal or better reliability using logs, metrics, alerts, and targeted profiling, without the distributed tracing tax.

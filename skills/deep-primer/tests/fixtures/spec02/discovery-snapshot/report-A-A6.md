# contrarian-seed — wave A (brief A-A6)

# Against Callouts and Exploded Views: The Skeptic's Case

The dominant approach of using callout annotations with leader lines and exploded-view diagrams for parts catalogues faces mounting criticism on accessibility, cognitive science, scalability, and technical grounds.

## Accessibility Failure

Callout annotations create fundamental barriers for screen reader users. Documented issues show callout components fail to properly expose contents to assistive technology—focus doesn't automatically trigger screen reader output of annotation text (GitHub issue #631, Office UI Fabric). When callouts are embedded in PDFs, annotations exist on a layer above the tagging tree, making them invisible to screen readers. This violates Section 508 compliance and WCAG standards. The W3C's WAI-ARIA Graphics Module provides workarounds, but traditional callout-based documentation rarely implements them. **3 independent sources confirm this barrier.**

## Cognitive Overload

A 2024 survey on annotations in information visualization (arxiv.org/pdf/2410.05579) documents that while annotations *can* aid comprehension, excess visual clutter increases cognitive load and degrades task performance. Visual clutter is defined as "the state in which excess items lead to degradation of performance." Multiple callouts on complex parts diagrams force users to parse spatial relationships between callout labels and leader lines, increasing perceptual load. The research indicates callouts work best for *minimal* annotation; parts catalogues with dozens of callouts per view violate this principle. **2 independent academic sources support this concern.**

## Labor Cost Unsustainability

Manual creation of exploded views remains time-consuming and error-prone. Design professionals note that exploded views drawn without consistent perspective, scale, or domain conventions become misleading. More critically: manual annotation of parts for catalogue entry doesn't scale. A November 2024 paper (arxiv.org/pdf/2411.11285) demonstrates zero-shot automatic annotation using LLM-generated datasets and SAM (Segment Anything Model) achieves Dice Coefficient 0.9513 and IoU 0.9303—eliminating field imaging and manual annotation entirely for parts identification. This represents a 10×–100× speedup over manual labeling (sources: Latitude.so, Cleverx 2025 reports). Hybrid human-in-loop approaches now replace manual-only workflows. **3+ independent sources document this transition.**

## Technical Capability Inversion

Vision-language models now identify specific parts with 100% accuracy (documented in medical imaging with GPT-4o and Gemini 1.5 Pro identifying surgical instruments). YOLOv12 (2025) integrated transformers and attention, narrowing the gap with SAM, which struggles primarily with speed (55× slower) rather than accuracy (12× superior boundary stability per Medium analysis). The emerging consensus: callout-based human annotation is increasingly redundant when zero-shot segmentation generates masks automatically. **2+ independent sources on VLM performance; 1 source on YOLO/SAM trade-offs.**

## The Scaling Problem

Most instance-level segmentation algorithms require domain-specific fine-tuning. But the new paradigm eliminates this redundancy: LLM-generated synthetic datasets, combined with SAM, achieve production accuracy without manual annotation. This directly undermines the justification for manual callout systems—they existed because alternatives didn't work at scale. That premise is no longer true as of 2024–2025. **1 primary source (arxiv 2411.11285); 2 supporting vendor trends.**

## The Verdict

Skeptics argue the callout/exploded-view model is optimized for pre-digital manufacturing documentation. Its accessibility failures, cognitive overhead, and labor cost are defensible only in the absence of better alternatives. Those alternatives—SAM, zero-shot annotation, vision-language models—now exist and scale. The dominant approach persists through institutional inertia, not technical merit.

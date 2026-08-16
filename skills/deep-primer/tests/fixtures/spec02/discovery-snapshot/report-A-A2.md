# debates — wave A (brief A-A2)

# Callout/Leader-Line Reading and Exploded-View Part Segmentation: Open Controversies

## State of the Field

Callout and leader-line reading remains the least-studied sub-problem in technical diagram understanding. While symbol detection has achieved 85%+ accuracy, the connecting visual elements—callouts, leader lines, and their relationships to parts—remain fundamentally unsolved. Annotation disagreement itself is a primary failure mode: manually marked leader lines often contain zigzag noise from scanning, and there is **no consensus protocol** for line-boundary definitions, creating inconsistency even in ground truth.

## Key Unsolved Problems

### Callout and Leader-Line Detection

**Contrast sensitivity remains the hard frontier.** Both classical methods (LSD, 2012; EDLines, 2008) and modern deep approaches fail systematically on low-contrast lines common in technical drawings. EDLines trades LSD's theoretical robustness for 10× speed by extracting edges first, but edge extraction itself fails on thin callout lines. No unified approach handles the degradation modes of scanned legacy documents: blur, show-through, and barrel distortion from camera capture dominate ~40% of mobile-scanned technical catalogues.

**Crossing and occlusion create irreducible ambiguity.** When multiple leader lines cross—a norm in dense technical drawings—no system reliably separates them. Manual annotation protocols explicitly avoid crossing leader lines for legibility, but legacy documents violate this. Similarly, **distinguishing leader lines from geometric edges** lacks a consensus classifier: all systems treat this as a post-hoc filtering problem, not a core architectural feature.

**Enterprise tools do not extract.** Autodesk AutoCAD's annotation API creates leader lines but provides no reverse capability for scanned drawings. This creates a vendor moat: proprietary systems can parse their own output formats, but open-source and academic approaches remain bound to manual annotation or heuristic-based fallbacks.

### Exploded-View Part Segmentation

**Boundary ambiguity defeats evaluation consensus.** Current instance segmentation models (Detectron2, YOLO variants) struggle when parts share edges—unavoidable in exploded views. YOLOv11 achieves 96.65% precision on P&ID symbols but fails to 40–60% recall on small or custom parts. Critically, no standardized metric exists for "near-miss" masks that are 95% correct but fail at exact boundaries. The DRAGON benchmark (diagram reasoning) accepts 8–12% label noise even after 2-annotator arbitration, primarily from disagreement on part granularity: should a screw assembly (head + shaft + threads) count as one part or three? Different technical manuals annotate differently, and no benchmark enforces consistency.

**Sketch vs. rendered ambiguity breaks modern segmentation.** SAM (Segment Anything Model v1.0) exploits photorealistic texture cues but hand-drawn exploded views—common in legacy manuals—lack them. SAM's "everything mode" uses grid-based prompting, which suffers from "localization blindness" on small or densely packed parts. More fundamentally, 2D projections in exploded views use non-isometric perspective for clarity; this breaks rigid 3D-to-2D projection assumptions that classical computer vision relies on.

**Cross-domain generalization fails completely.** YOLOv11 fine-tuned on automotive parts fails on furniture, medical devices, and machinery. Few-shot learning is emerging as the only viable path, but few-shot symbol detection in engineering drawings (2024) reports ~15% error rate even with meta-learning.

### Document Understanding and OCR at the Intersection

**Vision language models systematically ignore spatial localization.** VLMs like GPT-4V achieve >90% accuracy on text-in-image tasks but fail at fine-grained spatial reasoning. A 2024 study reveals that VLMs attend to text labels but ignore the spatial positions that encode meaning in parts catalogues. Relationship extraction—connecting symbols to images and callouts—drops 25+ percentage points below symbol detection (85%+ accuracy), with no standardized evaluation metric for partial correctness.

**Reading order remains unsolved.** The 2024 work on layout reading order establishes this as an open problem, especially in parts catalogues where callout numbers intentionally violate spatial order to save space. Donut (Document Understanding Transformer, CVPR 2023) works on receipts but fails on non-rectangular layouts. LayoutLMv3 struggles with reading order in non-left-to-right diagrams and requires layout annotations as input.

**Mixed handwritten+printed text has no unified solution.** Print-style handwriting achieves 10–15% higher accuracy than cursive in mixed-text recognition (2024 work), but no single model handles both without domain-specific retraining. This directly impacts field-annotated technical manuals.

## Consensus and Disagreement

**Consensus exists on:**
- Line detection via contrast-based methods fails on low-contrast elements
- Symbol detection and part boundary delineation require distinct architectures
- Data scarcity (no large-scale public parts catalogue benchmark) forces few-shot learning

**No consensus on:**
- Relationship extraction methodology (graph-based vs. sequence-to-sequence vs. hybrid)
- Part granularity in hierarchical assemblies
- Metric design for partial correctness in boundary tasks
- Annotation protocols for dense assemblies

## Practical Reality

Proprietary CAD systems dominate; open-source alternatives handle their own output formats but cannot reverse-engineer legacy scanned documents. Enginuity (50K engineering diagrams, 2024) includes only 2,056 manual-to-parts-table pairs due to confidentiality; commercial parts catalogues remain closed. The field remains fragmented across military (60 NIST diagrams), industrial, automotive, and consumer contexts, each with different annotation practices and failure modes.

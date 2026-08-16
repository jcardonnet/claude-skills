# recency-frontier — wave A (brief A-A3)

## Recent Advances in Technical Drawing & Parts Catalogue Understanding (Feb 2024–Aug 2025)

### Callout & Leader-Line Reading

Callout and leader-line detection—identifying annotation bubbles connected by thin lines to dimensions, GD&T specifications, or assembly callouts—has progressed from manual drafting to AI-assisted workflows. The SOTA shift is **integration rather than replacement**: modern tools now embed callout detection as part of broader engineering drawing extraction pipelines. Revit 2025 (released 2025) introduced advanced callout view functionality with improved geometry linking. The real acceleration comes from combining object detection (YOLO11, DINO-X) with layout-aware vision-language models, enabling both callout *identification* and *semantic understanding* of what they reference. Leader-line tracing via computer vision remains less publicly documented than parts segmentation, but is implemented in production CAD extraction systems (Altium Designer, BricsCAD).

### Exploded-View Part Segmentation: Major SOTA Shifts

**P3-SAM (September 2025)** represents the first native 3D part segmentation breakthrough. Released by Tencent Hunyuan, it achieves point-promptable 3D instance segmentation with IoU prediction on 3.7M labeled models. Prior work required either generic 3D instance segmentation models (inferior for parts) or manual annotation; P3-SAM provides precise part boundaries and reduces over-segmentation—critical for assembly documentation.

**BANG (July 2025, ACM ToG)** offers a complementary generative approach: it learns part-level 3D decomposition with smooth exploded-view generation via fine-tuned diffusion. Users provide spatial prompts (bounding boxes, surface regions); the model automatically generates exploded configurations optimized for 3D printing or assembly visualization. This represents a shift from static segmentation to *dynamic exploded geometry*.

**SAM2 (August 2024)** underpins both: it achieves 6× speedup over original SAM with streaming memory for real-time video segmentation. The 3× larger SA-V dataset (35.5M masks, 50.9K videos) enables more robust part tracking in assembly sequences.

### 2D-to-3D Technical Drawing Extraction

**HistCAD (February 2025)** provides the industry's first large-scale constraint-aware CAD dataset: 170,236 modeling sequences including 8,141 industrial parts from Siemens NX (closed-form representation). It bridges 2D engineering drawings to editable 3D CAD by preserving parametric constraints—critical for parts catalogues where users need to regenerate variants. **SOV-CAD (July 2025)** extends this with orthographic-view-guided reconstruction, using side/front/top views to guide 3D CAD sequence generation.

YOLOv8-OBB (Oriented Bounding Boxes) is the production SOTA for PMI (Product Manufacturing Information) extraction from 2D drawings, with reported 90.9% mAP on tiled small-parts detection.

### Document AI for Parts Catalogues

**UDOP** (Unified Document Processing, Dec 2022 → March 2024 HF integration) remains the reference for multi-task document understanding. It ranks #1 on the Document Understanding Benchmark (DUB) across 9 tasks.

**Florence-2 (CVPR 2024)** offers a lightweight alternative: 0.77B–3B models running on T4 GPUs with MIT license. It outperforms Kosmos-2 on zero-shot OCR, object detection, and grounding. **dots.ocr (July 2025)** and **DeepSeek-OCR (2025)** are new open-source vision-language OCR models with SOTA text extraction; dots achieves structured Markdown/JSON output; DeepSeek handles 200k pages/day at 3B parameters.

### What Changed in 6–12 Months

1. **3D segmentation became prompt-based** (SAM2, P3-SAM) rather than class-specific models.
2. **Exploded views shifted to generative** (BANG) from static pre-computed layouts.
3. **CAD reconstruction became constraint-aware** (HistCAD + LLMs), enabling editable, industrial-grade output.
4. **Document OCR commoditized**: three independent MIT/open-source OCR releases in 2025 (dots, DeepSeek, earlier releases).
5. **Callout detection integrated into VLM pipelines** rather than standalone, enabling semantic understanding of annotations.
6. **Sequential Mask R-CNN models remain SOTA for production** (auto parts, PCB defects) but yield to one-shot YOLO for real-time throughput.

### Deprecated Approaches

- **Manual PDF-to-CAD conversion**: Replaced by automated PMI extraction (YOLO + OCR).
- **LayoutLMv1/v2**: Superseded by LayoutLMv3, UDOP, Florence-2 (broader capabilities, open-source).
- **Sequential-only instance segmentation**: Two-stage Mask R-CNN hard to accelerate; replaced by one-shot YOLO models in production.
- **Manual assembly documentation**: Increasingly automated via exploded-view generation (BANG) and constraint-aware CAD reconstruction (HistCAD).

### Release Dates & Versions

- SAM2: August 2024 (arXiv), ICLR 2025 conference
- DINO-X: May 2025 latest revision (Nov 2024 submission)
- P3-SAM: September 2025 (arXiv 2509.06784)
- BANG: July 2025 (ACM Transactions on Graphics)
- HistCAD: February 2025 (arXiv 2602.19171)
- Florence-2: CVPR 2024
- dots.ocr: July 2025
- YOLO11: 2025

**Market context**: Document AI market is USD 14.66B (2025) → USD 27.62B (2030 proj.), driven by VLM adoption for multi-modal understanding.

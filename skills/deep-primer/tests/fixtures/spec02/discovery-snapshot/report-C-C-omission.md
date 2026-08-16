# practitioner — wave C (brief C-C-omission)

## Missing Aspects in Parts Catalogue Primers: Callout/Leader-Line Reading and Exploded-View Segmentation

### Six Critical Gaps

**1. Semantic Linking of Callout IDs Across Multiple Views (3 independent sources)**
Current primers treat callouts in isolation per view. Industry practice requires bidirectional callout-ID mapping across orthogonal projections, cross-sections, and exploded variants. A component labeled "A7" in exploded view must resolve to the same part in assembly view—no standard method exists for view-to-callout persistence in CAD→PDF→OCR pipelines.
Sources: ASME Y14.5-2018 (technical drawing standards), ISO 1101 (annotation conventions), CAD documentation workflow studies.

**2. OCR-Resistant Annotation Design (2 sources)**
Thin leader lines and small callout text consistently fail extraction in Tesseract/PaddleOCR. Primers omit design guidelines: minimum line weight, font rendering requirements, contrast thresholds. Critical for digitization workflows.
Sources: Document-AI best practices, OCR failure-mode analysis.

**3. Part Hierarchy Disambiguation in Nested Assemblies (2 sources)**
Primer gap: how to distinguish callout targets (component vs. subassembly group) and encode transitive part ownership when subassemblies contain parts. Prevalent in aerospace/automotive catalogues.
Sources: MIL-STD-1388-1A (Integrated Logistics Support standards), practitioner interviews.

**4. Geometric Centerline vs. Visual Callout Placement (2 sources)**
Exploded views separate geometric identity from visual readability. Primers ignore the mismatch between part position (for engineering) and leader-line attachment (for print)—breaks vision-model part-matching downstream.
Sources: SAM fine-tuning studies, CAD→schematic extraction pipelines.

**5. Multi-Scale Catalogue Callout Scope Rules (1–2 sources)**
Catalogues with zoom levels (overview → sub-system → component detail) lack formalized rules for in-scope callouts per level and overlapping callout fields.
Sources: Technical illustration standards, scalable document design patterns.

**6. Unresolvable Reference Handling (1 source)**
No guidance on fallback rendering when callout IDs lack legend entries, leader lines point to blank space, or parts lack callouts—affects BOM generation and parts database linkage.
Sources: Digital preservation and data-quality standards.

### Practitioner-Specific Gaps

- **1:N Callout Mappings:** Multi-part callouts ("fasteners A–D") and conditional callouts ("use if rev > 2.0") lack disambiguation logic.
- **OCR Preprocessing:** No guidance on line thinning, contrast enhancement, or synthetic training data for vision models.
- **Tool Pipeline Integration:** Missing patterns for PDFPlumber + Tesseract, Vision Transformers for callout detection, SAM for component segmentation, and LLM-based entity linking ("callout A7" → catalogue entry).

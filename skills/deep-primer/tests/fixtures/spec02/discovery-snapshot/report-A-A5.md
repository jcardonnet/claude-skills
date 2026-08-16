# adjacent-field — wave A (brief A-A5)

## Adjacent Fields for Callout/Leader-Line Reading & Exploded-View Part Segmentation

### Core Borrowed Domains (9 fields, 3+ independent sources each)

**Technical Drawing Standards (ISO 128 family, 4 sources)** establish explicit conventions for leader lines, callout placement, and annotation hierarchy. ISO 128-2:2020 (current) directly specifies these practices, contrasting with ad-hoc approaches in graphic design.

**Technical Illustration** (6 sources) contributed the exploded-view technique itself—a method combining artistic composition with mechanical accuracy to show assembly relationships. This borrows spatial decomposition principles.

**Information Design** (3 sources) provided the callout concept: text-linked-by-line to specific locations. Annotation hierarchy and visual attention principles are direct transfers.

**Document Layout Analysis (CV, 5 sources)** contributes region detection and spatial segmentation methods. Tools like YOLO v11, LayoutLMv3 (Microsoft), and Faster R-CNN perform similar tasks but on different visual inputs.

**CAD Standards (ISO 10303 STEP, 5 sources)** supply the 3D source geometry for exploded views. SolidWorks/AutoCAD/Creo (2026 versions) generate assembly structures that catalogs visualize.

**Electronic Parts Catalogs (2 sources)** contributed parts hierarchy and numbering schemes, defining how components reference each other.

**Product Data Management (3 sources)** introduced formal ontologies (ISO 13584 PLIB) for parts relationships and interoperability.

**Technical Documentation Standards** (4 sources): S1000D (aerospace) and DITA (topic-based) contributed modular document structure and multi-language support patterns.

**Vision-Language Models** (4 sources, emerging 2024–2026): Qwen3-VL, GLM-4.5V, Pixtral 12B now enable semantic linking of text callouts to visual components.

### False Friends (Superficially Similar, Fundamentally Different)

**Semantic Segmentation (CV) vs. Parts Segmentation:** Standard models fail on technical drawings. ImageNet-trained YOLO/Faster R-CNN misidentify clean-line drawings as noise. Technical drawings require simpler algorithms exploiting high contrast and simple geometry.

**Form Field Detection vs. Annotation Detection:** Forms encode label↔field adjacency; parts catalogs encode text→line→component geometric linking. Different relationship models.

**Line Detection (General) vs. Technical Leader Lines:** Canny/Hough edge detection fails on technical drawings; leader-line detection exploits drawing-specific properties.

**UML Diagrams vs. Technical Drawings:** UML is topology-based (abstract software); technical drawings are geometry-based (concrete mechanics). Different precision requirements.

**Patent Drawings vs. Parts Catalogues:** Patents prove invention scope (legal); catalogs enable identification and replacement (product use). Different standards (USPTO/WIPO/EPO diverge) and annotation levels.

**Medical vs. Technical Illustration:** Medical illustration is formally certified (CAAHEP-accredited); technical illustration has no formal credential standard. Different knowledge domains.

**GIS/Cartography vs. Parts Annotation:** GIS uses geographic coordinates (ISO 19100, 50+ standards); parts use relative assembly positions (ISO 128). Opposite coordinate models.

**Graphic Design vs. Technical Illustration:** Graphic design prioritizes aesthetics; technical illustration prioritizes accuracy. Applying design principles breaks correctness.

**Automatic Graph Drawing vs. Exploded Layout:** Graph drawing optimizes abstract topology; exploded views preserve geometric meaning. Success metrics are opposite.

### Key Distinguishing Factors

- **Precision:** Parts catalogs demand 99%+ accuracy; CV segmentation targets 80–90%.
- **Visual Signal:** High-contrast, clean-line technical drawings ≠ photographic images.
- **Relationship Model:** Spatial geometric linking ≠ topology or semantic classification.
- **Standardization:** Formal ISO/aerospace standards vs. emergent design practices.
- **Standards Timeline:** ISO 128-2:2020, ISO 10303 (1994, updated continuously), YOLO v11 (2024), Vision-language models (Qwen3-VL Jan 2026).

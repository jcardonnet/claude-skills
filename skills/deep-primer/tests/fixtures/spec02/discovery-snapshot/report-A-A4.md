# source-authority — wave A (brief A-A4)

# Callout/Leader-Line Reading and Exploded-View Part Segmentation for Parts Catalogues: Source-Authority Research Brief

## Normative Frameworks and Technical Standards

Leader-line annotation in technical drawings is governed by ISO 128-2:2020 (formerly BS EN ISO 128-2), the international standard specifying types of lines in technical drawings and rules for leader and reference lines (3 independent sources confirm this standard's authority). Key practices include: drawing leader lines at angles to drawing elements (avoiding parallel alignment), with 15° increments recommended; never allowing annotation leaders to cross; positioning instruction text centered or above reference lines at 2× line thickness minimum; using arrowheads for physical edges/surfaces and dots for areas/volumes (2 primary sources document these conventions).

For parts catalogues specifically, ISO 7573:2008 governs technical product documentation parts lists, while S1000D (Issue 6.0+) is the international specification for aerospace/defense technical publications, prescribing data modules with unique identification codes and supporting illustrated parts data with interactive hotspots (callout annotations linked to parts lists).

## Identification and Annotation in Illustrated Parts Catalogues

Identification numbers appear in circles/balloons connected by leader lines to parts in assembly drawings and catalogues. Best-practice layout positions illustrations on one side with corresponding parts tables on the other to avoid reader frustration (2 independent practitioner sources). Callout annotations in S1000D serve as responsive hyperlinks, enabling navigation between illustrated areas and parts lists or detailed views—extending classical leader-line reading into interactive digital contexts (1 primary source).

## Computer Vision and Automated Callout Detection

Symbol and callout detection in engineering drawings has evolved from classical image processing (Hough transform for line detection, binarization, morphological operations—3 sources) to deep learning approaches. YOLO-based systems achieve 70–85% accuracy in detecting annotation groups and text/symbol recognition in 2D drawings (2 academic sources). Recent research (2023–2025) demonstrates:

- **Tolerancing Callout Detection:** Computer vision models extract tolerancing callout blocks and symbols using CNNs, random forests, and SVMs (1 peer-reviewed paper).
- **Few-Shot and Keypoint Methods:** Comparisons of YOLOv7-Pose, Keypoint R-CNN, and custom two-stage approaches for precise symbol localization (1 academic paper, 2024).
- **Graph-Based Enhancement:** Graph-based refinements improve detection of graphic symbols and interconnections in circuit and instrumentation diagrams (2 sources, 2023–2025).
- **GPTR (Gestalt-Perception Transformer):** A transformer-based approach (2023) addressing the sparse research in diagram object detection versus abundant natural-image detection literature.

## Document Layout Analysis and Part Segmentation

Instance segmentation for parts and layout analysis has accelerated with foundation models. The Segment Anything Model (SAM) and its adaptations—Hi-SAM (hierarchical text segmentation), ET-SAM (scene text detection), and DocSAM (document image segmentation)—enable multi-granularity part identification and layout classification (3 academic sources, 2024–2025). Modern tools (Docling, with MIT license and 10,000+ GitHub stars; DocLayout-YOLO; DLAFormer) automate extraction of document elements into predefined taxonomies (2 sources, 2024–2025).

Classical text-line extraction and baselines (core prerequisites for parts-list alignment) use fully convolutional networks and energy minimization, with binarization remaining a foundational preprocessing step (3 sources spanning document analysis theory).

## End-to-End Pipelines and Manufacturing Integration

Recent research (2025 PLM conference, Design Society) demonstrates end-to-end conversion pipelines: automated extraction of 2D drafting annotations using location data relative to 3D CAD models, directly feeding results into quality-control databases to reduce manual verification time (1 primary conference paper). Hand-drawn sketch interpretation frameworks extract beam diagrams and structural features for automated analysis (1 peer-reviewed source, 2024).

## Practitioner and Accessibility Considerations

Annotation design for technical documentation emphasizes: (1) narrative flow—tying callout count and placement to reading order for comprehension (1 peer-reviewed design study, 2025); (2) accessibility—providing alt text for annotated screenshots describing not just visual elements but the action each callout directs (1 best-practice source, 2026); (3) maintenance—checkpoints to re-annotate affected documentation after releases (1 practitioner guide, 2026).

## Summary of Supporting Source Counts

- ISO 128-2:2020 leader-line standards: 3 independent confirmations
- Best-practice layout/visual design: 4 sources (practitioner + academic)
- YOLO-based symbol detection: 2 academic papers
- Transformer/SAM-based segmentation: 3+ recent papers (2024–2025)
- Classical image-processing techniques: 3+ historical/foundational sources
- End-to-end manufacturing pipelines: 1 primary conference source, emerging category
- Accessibility and design: 2 sources (emerging emphasis)

No significant disagreements found; research converges on ISO 128-2 compliance, YOLO/transformer-based automation, and interactive digital extension of classical leader-line conventions.

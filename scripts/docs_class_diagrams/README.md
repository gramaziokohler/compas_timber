# Class diagram pipeline

Regenerates `docs/contribution/class_diagrams.md` from the source code, so the diagrams
cannot drift from (or hallucinate) the actual class structure.

The pipeline splits the work between deterministic extraction and curated abstraction:

1. `extract_classes.py` parses `src/compas_timber` with Python's `ast` and writes
   `graph.json` — classes, bases, attributes (with `@property` getters folded in),
   method signatures, stereotypes. This is ground truth; relationships are never guessed.
2. `diagram_spec.py` is the curated part: subsystem partitioning, section prose, external
   anchor classes (`Model`, `Element`, `Data`, ...), stereotype overrides (e.g.
   abstract-by-convention classes), and cross-class edges. Composition edges declared with
   an attribute name are asserted against `graph.json`, so they fail loudly if the code changes.
3. `gen_diagrams.py` merges both (plus attribute types parsed from numpydoc docstrings)
   and writes `docs/contribution/class_diagrams.md`.
4. `validate_mermaid.py` lints every mermaid block (and renders them if
   `@mermaid-js/mermaid-cli` is installed).
5. `compare_doc_to_graph.py` diffs any diagrams doc against `graph.json` and reports
   classes/edges/members that don't exist in the code, plus per-block coverage gaps.

## Usage

From this directory:

```bash
python extract_classes.py ../../src/compas_timber --out graph.json
python gen_diagrams.py
python validate_mermaid.py ../../docs/contribution/class_diagrams.md
python compare_doc_to_graph.py ../../docs/contribution/class_diagrams.md graph.json
```

After adding/renaming classes, rerun the extraction + generation and review the diff.
New classes that should appear in a diagram must be added to the class lists in
`diagram_spec.py` (the compare script's coverage report tells you what's unplaced).
`graph.json` is a build artifact — no need to commit it.

"""Diff the mermaid class diagrams in a markdown doc against the AST-extracted graph.json.

Reports, per mermaid block:
- inheritance edges in the doc that do NOT exist in the code (hallucinations)
- classes in the doc that do not exist in the code
- doc attributes/methods that do not exist on the class (or its extracted members)
- classes/edges in the code that the doc omits (gaps), scoped to the modules the block covers
"""

import json
import re
import sys
from collections import defaultdict

EXTERNAL = {
    # anchors from compas / compas_model / stdlib that graph.json won't contain
    "Model", "Element", "Data", "Exception", "Geometry", "Shape", "Graph",
}

def parse_mermaid_blocks(md_text):
    blocks = []
    # capture preceding "## Heading" for context
    sections = re.split(r"^## ", md_text, flags=re.M)
    for sec in sections[1:]:
        title = sec.splitlines()[0].strip()
        for m in re.finditer(r"```mermaid\n(.*?)```", sec, re.S):
            blocks.append((title, m.group(1)))
    return blocks

def parse_block(body):
    classes = {}  # name -> {"members": [..], "stereotypes": [..]}
    edges = []    # (parent, child) for <|--
    other_rels = []
    cur = None
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%") or line == "classDiagram":
            continue
        m = re.match(r"class\s+([A-Za-z_][\w]*)\s*\{?", line)
        if m and "<|--" not in line and "--" not in line.replace("--", "", 0):
            name = m.group(1)
            classes.setdefault(name, {"members": [], "stereotypes": []})
            cur = name if line.endswith("{") else None
            continue
        if line == "}":
            cur = None
            continue
        em = re.match(r"([\w]+)\s*<\|--\s*([\w]+)", line)
        if em:
            edges.append((em.group(1), em.group(2)))
            cur = None
            continue
        rm = re.match(r"([\w]+)\s*(\.\.>|--\*|\*--|o--|--o|-->)\s*([\w]+)\s*(?::\s*(.*))?", line)
        if rm:
            other_rels.append((rm.group(1), rm.group(2), rm.group(3), rm.group(4)))
            cur = None
            continue
        if cur:
            sm = re.match(r"<<(\w+)>>", line)
            if sm:
                classes[cur]["stereotypes"].append(sm.group(1))
            else:
                classes[cur]["members"].append(line)
    return classes, edges, other_rels

def member_name(member_line):
    m = re.match(r"[+\-#~]?\s*(\w+)", member_line)
    return m.group(1) if m else None

def main(doc_path, graph_path):
    md = open(doc_path, encoding="utf-8").read()
    g = json.load(open(graph_path, encoding="utf-8"))
    code_classes = {c["name"]: c for c in g["classes"]}
    code_edges = set()
    for e in g["inheritance"]:
        code_edges.add((e["parent"], e["child"]) if isinstance(e, dict) else tuple(e))
    # also build parent->child from per-class bases (robust to inheritance list shape)
    for c in g["classes"]:
        for b in c.get("bases", []):
            code_edges.add((b.split(".")[-1], c["name"]))

    # members per class, including inherited? No — per-class only; we also allow base-class members
    def class_member_names(cname, seen=None):
        seen = seen or set()
        if cname in seen or cname not in code_classes:
            return set()
        seen.add(cname)
        c = code_classes[cname]
        names = {a["name"] for a in c.get("attributes", [])}
        names |= {m["name"] for m in c.get("methods", [])}
        for b in c.get("bases", []):
            names |= class_member_names(b.split(".")[-1], seen)
        return names

    problems = 0
    for title, body in parse_mermaid_blocks(md):
        classes, edges, rels = parse_block(body)
        print(f"\n=== {title} ===")
        # 1. classes not in code
        for name in classes:
            if name not in code_classes and name not in EXTERNAL:
                print(f"  [DOC-ONLY CLASS] {name}")
                problems += 1
        # 2. edges not in code
        for parent, child in edges:
            if parent in EXTERNAL and child in code_classes:
                # verify child really has that external base
                bases = [b.split(".")[-1] for b in code_classes[child].get("bases", [])]
                if parent not in bases:
                    print(f"  [BAD EDGE] {parent} <|-- {child} (actual bases: {bases})")
                    problems += 1
                continue
            if child in code_classes:
                bases = [b.split(".")[-1] for b in code_classes[child].get("bases", [])]
                if parent not in bases:
                    print(f"  [BAD EDGE] {parent} <|-- {child} (actual bases: {bases})")
                    problems += 1
            elif child not in EXTERNAL:
                print(f"  [EDGE TO DOC-ONLY CLASS] {parent} <|-- {child}")
                problems += 1
        # 3. members not in code
        for name, info in classes.items():
            if name not in code_classes:
                continue
            valid = class_member_names(name)
            for mline in info["members"]:
                mn = member_name(mline)
                if mn and mn not in valid and not mn.startswith("SUPPORTED") and mn not in ("MIN_ELEMENT_COUNT", "MAX_ELEMENT_COUNT", "PROCESSING_NAME"):
                    # class-level constants often not extracted; only flag lowercase members
                    if mn != mn.upper():
                        print(f"  [BAD MEMBER] {name}.{mn}  ({mline})")
                        problems += 1
        # 4. gaps: code classes sharing a base with doc classes but missing from doc
        doc_names = set(classes)
        # find subsystem modules covered by this block
        mods = {code_classes[n]["module"].split(".")[0] for n in doc_names if n in code_classes}
        for cname, c in code_classes.items():
            if c["module"].split(".")[0] in mods and cname not in doc_names:
                print(f"  [MISSING FROM DOC] {cname} ({c['module']})")
    print(f"\nTotal hard problems (excl. missing): {problems}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

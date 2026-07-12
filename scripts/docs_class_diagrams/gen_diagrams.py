"""Generate docs/contribution/class_diagrams.md from graph.json (AST ground truth).

Class bodies (attributes, methods, inheritance) come mechanically from graph.json.
Attribute types are merged in from numpydoc docstrings parsed straight from source.
Only the subsystem partitioning, prose, anchors, stereotype overrides and
cross-class dependency edges are curated below - and curated composition edges are
asserted against the extracted attributes so they cannot go stale silently.
"""

import ast
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
SRC = os.path.join(_REPO, "src", "compas_timber")
GRAPH = os.path.join(_HERE, "graph.json")
OUT = os.path.join(_REPO, "docs", "contribution", "class_diagrams.md")

# ---------------------------------------------------------------- docstring types

ROLE_RE = re.compile(r":class:`~?([\w\.]+)`")


def clean_type(t):
    t = t.strip()
    t = re.sub(r",?\s*optional\s*(\(default[^)]*\))?\s*$", "", t)
    t = re.sub(r",?\s*read-only\s*$", "", t)
    t = re.sub(r",?\s*default\s+\S+\s*$", "", t)
    # {AlignmentType.BOTTOM, AlignmentType.CENTER, ...} -> AlignmentType
    m = re.match(r"^(?:str\s*)?\{?\s*(\w+)\.\w+\s*[,}]", t)
    if m:
        return m.group(1)
    # literal, one of JointTopology... -> JointTopology
    t = re.sub(r"^literal,?\s*(one of\s*)?", "", t)
    # :class:`~compas.geometry.Plane` -> Plane (tolerate spaces/quotes/missing ticks)
    t = ROLE_RE.sub(lambda m: m.group(1).split(".")[-1], t)
    t = re.sub(r":\s*class:\s*[`'\"]?~?([\w\.]+)[`'\"]?", lambda m: m.group(1).split(".")[-1], t)
    # list(X) / list of X / tuple (X) ... -> bracket style
    t = re.sub(r"\b(list|tuple|set|dict|generator|Generator)\s+\(", lambda m: m.group(1) + "(", t)
    for _ in range(2):
        t = re.sub(r"\b(list|tuple|set|dict|generator|Generator)\(([^()]*)\)", lambda m: f"{m.group(1)}[{m.group(2)}]", t)
    t = re.sub(r"\b(list|tuple|set)s? of ([\w\.\[\]]+)", lambda m: f"{m.group(1)}[{m.group(2).split('.')[-1]}]", t)
    t = t.replace("`", "").replace("~", "").strip().rstrip(",")
    # multiline / overly long types get truncated at first " or "
    if len(t) > 40 and " or " in t:
        t = t.split(" or ")[0].strip()
    # last-resort safety: unbalanced braces/parens would break mermaid parsing
    if t.count("{") != t.count("}") or t.count("(") != t.count(")"):
        t = re.sub(r"[{}()]", "", t).strip()
    return t


def docstring_attr_types():
    """{class_name: {attr_name: type}} parsed from numpydoc Attributes sections."""
    result = {}
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "rhino")]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                doc = ast.get_docstring(node) or ""
                types = {}
                in_attrs = False
                lines = doc.splitlines()
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped in ("Attributes", "Parameters") and i + 1 < len(lines) and set(lines[i + 1].strip()) == {"-"}:
                        in_attrs = True
                        continue
                    if in_attrs:
                        if set(stripped) == {"-"}:
                            continue
                        if re.match(r"^[A-Z][A-Za-z ]+$", stripped) and i + 1 < len(lines) and set(lines[i + 1].strip()) == {"-"}:
                            in_attrs = False
                            continue
                        m = re.match(r"^(\w+)\s*:\s*(.+)$", stripped)
                        if m and not line.startswith(" " * 8):
                            types.setdefault(m.group(1), clean_type(m.group(2)))
                if types:
                    result.setdefault(node.name, {}).update(types)
    return result


# ---------------------------------------------------------------- rendering

GLOBAL_METHOD_EXCLUDES = {"__init__", "compute_modelgeometry", "compute_modeltransformation"}
KEEP_CONSTANTS = {"SUPPORTED_TOPOLOGY", "MIN_ELEMENT_COUNT", "MAX_ELEMENT_COUNT"}


def clean_param(p):
    p = p.strip()
    if "=" in p:
        name, default = p.split("=", 1)
        name = name.split(":")[0].strip()
        return f"{name}={default.strip()}"
    return p.split(":")[0].strip()


def ancestor_members(cls, by_name, seen=None):
    """Names of members declared on in-package ancestors (for override suppression)."""
    seen = seen or set()
    names = set()
    for base in cls["bases"]:
        b = base.split(".")[-1]
        if b in seen or b not in by_name:
            continue
        seen.add(b)
        bc = by_name[b]
        names |= {a["name"] for a in bc["attributes"]}
        names |= {m["name"] for m in bc["methods"]}
        names |= ancestor_members(bc, by_name, seen)
    return names


def render_class(cls, dtypes, spec, by_name):
    name = cls["name"]
    over = spec.get("overrides", {}).get(name, {})
    stereos = list(cls["stereotypes"])
    for s in over.get("add_stereotypes", []):
        if s not in stereos:
            stereos.append(s)
    is_enum = "enumeration" in stereos
    exclude = set(over.get("exclude", ()))
    keep = set(over.get("keep", ()))
    include = over.get("include")  # explicit member allowlist (attrs+methods)
    inherited = ancestor_members(cls, by_name) - keep

    lines = [f"      class {name} {{"]
    for s in stereos:
        lines.append(f"         <<{s}>>")

    attr_names = set()
    for a in cls["attributes"]:
        an = a["name"]
        attr_names.add(an)
        if an.startswith("_") or an in exclude or (include is not None and an not in include):
            continue
        if an in inherited and an not in KEEP_CONSTANTS:
            continue
        caps = an == an.upper() and len(an) > 1
        if is_enum:
            if caps:
                lines.append(f"         {an}")
            continue
        if caps:
            if an in KEEP_CONSTANTS:
                val = a.get("value", "").replace("JointTopology.", "")
                lines.append(f"         +{an} = {val}" if val else f"         +{an}")
            continue
        t = a.get("type") or dtypes.get(name, {}).get(an, "")
        t = clean_type(t) if t else ""
        lines.append(f"         +{an} : {t}" if t else f"         +{an}")

    if not is_enum:
        seen = set()
        for m in cls["methods"]:
            mn = m["name"]
            if mn in GLOBAL_METHOD_EXCLUDES or mn in exclude or mn in attr_names or mn in seen:
                continue
            if mn.startswith("_") or (mn in inherited):
                continue
            if include is not None and mn not in include:
                continue
            seen.add(mn)
            params = ", ".join(clean_param(p) for p in m["params"] if not p.startswith("*") or True)
            ret = clean_type(m.get("returns", "")).strip("'\"")
            sig = f"         +{mn}({params})"
            if ret:
                sig += f" : {ret}"
            lines.append(sig)

    lines.append("      }")
    return lines


def render_diagram(spec, by_name, dtypes):
    lines = ["classDiagram"]
    included = list(spec["classes"])
    # anchors: name -> stereotype text (or None for bare)
    anchors = spec.get("anchors", {})
    for aname, stereo in anchors.items():
        if stereo:
            lines.append(f"      class {aname} {{")
            lines.append(f"         <<{stereo}>>")
            lines.append("      }")
        else:
            lines.append(f"      class {aname}")
        lines.append("")

    for cname in included:
        cls = by_name.get(cname)
        if cls is None:
            raise SystemExit(f"spec error: class {cname} not in graph.json")
        lines.extend(render_class(cls, dtypes, spec, by_name))
        lines.append("")

    all_names = set(included) | set(anchors)
    inh = []
    for cname in included:
        for base in by_name[cname]["bases"]:
            b = base.split(".")[-1]
            if b in all_names:
                inh.append(f"      {b} <|-- {cname}")
    if inh:
        lines.append("      %% Inheritance relationships")
        lines.extend(inh)
        lines.append("")

    extra = spec.get("edges", [])
    if extra:
        lines.append(f"      %% {spec.get('edges_title', 'Composition and usage relationships')}")
        for e in extra:
            if len(e) == 5:  # (owner, op, target, label, via_attr) - machine-checked
                owner, op, target, label, via = e
                attrs = {a["name"] for a in by_name[owner]["attributes"]}
                if via not in attrs:
                    raise SystemExit(f"spec error: {owner}.{via} not found (edge {owner} {op} {target})")
            else:
                owner, op, target, label = e
            lines.append(f"      {owner} {op} {target} : {label}" if label else f"      {owner} {op} {target}")
    while lines and lines[-1] == "":
        lines.pop()
    return "```mermaid\n" + "\n".join(lines) + "\n```"


def main():
    g = json.load(open(GRAPH, encoding="utf-8"))
    by_name = {c["name"]: c for c in g["classes"]}
    dtypes = docstring_attr_types()

    spec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagram_spec.py")
    ns = {}
    exec(compile(open(spec_path, encoding="utf-8").read(), spec_path, "exec"), ns)
    sections = ns["SECTIONS"]
    header = ns["HEADER"]

    parts = [header]
    for sec in sections:
        parts.append(f"## {sec['title']}\n")
        parts.append(sec["prose"].strip() + "\n")
        for dia in sec["diagrams"]:
            if dia.get("intro"):
                parts.append(dia["intro"].strip() + "\n")
            parts.append(render_diagram(dia, by_name, dtypes) + "\n")
    text = "\n".join(parts)
    open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    n_blocks = text.count("```mermaid")
    print(f"Wrote {OUT}: {len(text.splitlines())} lines, {n_blocks} diagrams")


if __name__ == "__main__":
    main()

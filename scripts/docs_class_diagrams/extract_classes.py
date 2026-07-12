#!/usr/bin/env python3
"""
Extract a faithful class graph from a Python codebase using the `ast` module.

Output is JSON: classes with their bases, attributes (name + inferred type),
methods (name + signature), stereotypes (abstract/enum/exception/dataclass),
and the source module of each class. Relationships (inheritance, composition)
are derived from parsed facts only -- nothing here is inferred by an LLM, so
the downstream diagram cannot invent edges that don't exist in the code.

Usage:
    python extract_classes.py <path-to-package-or-dir> [--out graph.json]

The result is meant to be read by an LLM, which then does the *abstraction*
(subsystem grouping, pruning) and writes Mermaid. This script does the
*fact-gathering*.
"""
import argparse
import ast
import json
import os
import sys
from typing import Optional


def unparse(node) -> str:
    """Best-effort source rendering of an AST node (annotations, defaults)."""
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def base_name(node) -> str:
    """Render a base-class expression: Name, Attribute (pkg.Class), Subscript (Generic[T])."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        # e.g. compas.data.Data -> keep only the final segment for diagram brevity,
        # but record the full path too for disambiguation.
        return node.attr
    if isinstance(node, ast.Subscript):
        return base_name(node.value)
    return unparse(node)


def full_base_path(node) -> str:
    if isinstance(node, ast.Attribute):
        return unparse(node)
    return base_name(node)


DECORATOR_STEREOTYPES = {
    "dataclass": "dataclass",
    "final": None,
}


def method_signature(fn: ast.FunctionDef) -> dict:
    """Build a readable signature: name(params) : return_type, plus visibility."""
    args = fn.args
    params = []

    posonly = getattr(args, "posonlyargs", [])
    all_pos = list(posonly) + list(args.args)

    # Compute which positional args have defaults (defaults align to the tail).
    num_defaults = len(args.defaults)
    default_start = len(all_pos) - num_defaults

    for i, a in enumerate(all_pos):
        if a.arg in ("self", "cls"):
            continue
        piece = a.arg
        if a.annotation is not None:
            piece += f": {unparse(a.annotation)}"
        if i >= default_start:
            d = args.defaults[i - default_start]
            piece += f"={unparse(d)}"
        params.append(piece)

    if args.vararg:
        params.append("*" + args.vararg.arg)
    for a in args.kwonlyargs:
        piece = a.arg
        if a.annotation is not None:
            piece += f": {unparse(a.annotation)}"
        params.append(piece)
    if args.kwarg:
        params.append("**" + args.kwarg.arg)

    ret = unparse(fn.returns)
    name = fn.name
    visibility = "-" if name.startswith("_") and not name.startswith("__") else "+"
    if name.startswith("__") and name.endswith("__"):
        visibility = "+"  # dunder: treat as public interface

    return {
        "name": name,
        "params": params,
        "returns": ret,
        "visibility": visibility,
        "is_property": any(
            (isinstance(d, ast.Name) and d.id == "property")
            for d in fn.decorator_list
        ),
        "is_static": any(
            (isinstance(d, ast.Name) and d.id in ("staticmethod", "classmethod"))
            for d in fn.decorator_list
        ),
        "is_abstract": any(
            ("abstractmethod" in unparse(d)) for d in fn.decorator_list
        ),
    }


def extract_class_attributes(cls: ast.ClassDef) -> list:
    """
    Collect attributes from:
      - class-level annotated assignments (x: int = 0)
      - class-level plain assignments (x = 0)  [enums, constants]
      - self.<name> = ... assignments inside methods (instance attributes)
    Deduplicated, first type annotation wins.
    """
    attrs = {}
    order = []

    def add(name, type_str, value_str=None):
        if name in attrs:
            # upgrade type if we previously had none
            if not attrs[name]["type"] and type_str:
                attrs[name]["type"] = type_str
            return
        attrs[name] = {"name": name, "type": type_str or "", "value": value_str or ""}
        order.append(name)

    for node in cls.body:
        # x: int = 0  or  x: int
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            add(node.target.id, unparse(node.annotation), unparse(node.value))
        # x = 0  (skip if it's a lambda/def-like; keep simple constants & enum members)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    add(t.id, "", unparse(node.value))

    # instance attributes: self.x = ...
    for node in ast.walk(cls):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (
                    isinstance(t, ast.Attribute)
                    and isinstance(t.value, ast.Name)
                    and t.value.id == "self"
                ):
                    add(t.attr, "", None)
        elif isinstance(node, ast.AnnAssign):
            t = node.target
            if (
                isinstance(t, ast.Attribute)
                and isinstance(t.value, ast.Name)
                and t.value.id == "self"
            ):
                add(t.attr, unparse(node.annotation), unparse(node.value))

    # Filter dunder + private (leading underscore) noise. Private instance state
    # is an implementation detail; the diagram documents the public interface.
    result = []
    for name in order:
        if name.startswith("_"):
            continue
        result.append(attrs[name])
    return result


def stereotypes_for(cls: ast.ClassDef, bases: list, all_class_names: set) -> list:
    st = []
    # abstract: inherits ABC/ABCMeta, or has @abstractmethod, or metaclass=ABCMeta
    src = ""
    has_abstractmethod = any(
        isinstance(n, ast.FunctionDef)
        and any("abstractmethod" in unparse(d) for d in n.decorator_list)
        for n in cls.body
    )
    # A method whose *entire* body is `raise NotImplementedError` is the classic
    # "abstract in spirit" idiom used across compas-style codebases.
    def raises_notimplemented(fn):
        body = [s for s in fn.body if not isinstance(s, ast.Expr) or not isinstance(s.value, ast.Constant)]
        return len(body) == 1 and isinstance(body[0], ast.Raise) and "NotImplemented" in unparse(body[0])

    has_notimplemented = any(
        isinstance(n, ast.FunctionDef) and raises_notimplemented(n) for n in cls.body
    )
    if (
        has_abstractmethod
        or has_notimplemented
        or any(b in ("ABC", "ABCMeta") for b in bases)
        or any("abc" in b.lower() for b in bases)
    ):
        st.append("abstract")
    # enum
    if any("enum" in b.lower() for b in bases):
        st.append("enumeration")
    # exception
    if any(b.endswith("Error") or b == "Exception" or b == "BaseException" for b in bases):
        st.append("exception")
    # dataclass
    if any(
        (isinstance(d, ast.Name) and d.id == "dataclass")
        or (isinstance(d, ast.Attribute) and d.attr == "dataclass")
        for d in cls.decorator_list
    ):
        st.append("dataclass")
    return st


def detect_compositions(cls_attrs: list, all_class_names: set) -> list:
    """
    Heuristic composition edges: if an attribute's type references another
    known class in the codebase, emit an edge. Handles List[X], list[X],
    tuple[X], X | None, Optional[X], dict[..., X].
    """
    edges = []
    for a in cls_attrs:
        t = a["type"]
        if not t:
            continue
        # pull identifiers out of the annotation
        try:
            tree = ast.parse(t, mode="eval")
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in all_class_names:
                edges.append({"target": node.id, "via": a["name"]})
            elif isinstance(node, ast.Attribute) and node.attr in all_class_names:
                edges.append({"target": node.attr, "via": a["name"]})
    # dedupe by target
    seen = set()
    out = []
    for e in edges:
        if e["target"] in seen:
            continue
        seen.add(e["target"])
        out.append(e)
    return out


def module_name_from_path(path: str, root: str) -> str:
    rel = os.path.relpath(path, root)
    rel = rel[:-3] if rel.endswith(".py") else rel
    parts = [p for p in rel.split(os.sep) if p != "__init__"]
    return ".".join(parts)


def collect_python_files(target: str) -> list:
    if os.path.isfile(target) and target.endswith(".py"):
        return [target]
    files = []
    for dirpath, dirnames, filenames in os.walk(target):
        # skip common noise
        dirnames[:] = [
            d
            for d in dirnames
            if d not in ("__pycache__", ".git", "build", "dist", ".venv", "venv", "node_modules", "tests", "test")
        ]
        for fn in filenames:
            if fn.endswith(".py"):
                files.append(os.path.join(dirpath, fn))
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="Path to a Python package, directory, or file")
    ap.add_argument("--out", default=None, help="Output JSON path (default: stdout)")
    ap.add_argument("--root", default=None, help="Root for module names (default: target)")
    args = ap.parse_args()

    root = args.root or (args.target if os.path.isdir(args.target) else os.path.dirname(args.target))
    files = collect_python_files(args.target)

    raw_classes = []  # (ast.ClassDef, module)
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"# skip {path}: {e}", file=sys.stderr)
            continue
        mod = module_name_from_path(path, root)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                raw_classes.append((node, mod))

    all_class_names = {c.name for c, _ in raw_classes}

    classes = []
    for cls, mod in raw_classes:
        bases = [base_name(b) for b in cls.bases]
        base_paths = [full_base_path(b) for b in cls.bases]
        attrs = extract_class_attributes(cls)
        all_methods = [
            method_signature(n)
            for n in cls.body
            if isinstance(n, ast.FunctionDef)
            and not (n.name.startswith("__") and n.name.endswith("__") and n.name != "__init__")
        ]
        # Fold @property getters into attributes (their return type is the attr type);
        # keep the rest as methods. Drop private methods from the public-interface view.
        existing_attr_names = {a["name"] for a in attrs}
        methods = []
        for m in all_methods:
            if m["is_property"]:
                if m["name"] not in existing_attr_names:
                    attrs.append({"name": m["name"], "type": m["returns"] or "", "value": ""})
                    existing_attr_names.add(m["name"])
            elif m["name"].startswith("_") and m["name"] != "__init__":
                continue
            else:
                methods.append(m)
        st = stereotypes_for(cls, bases, all_class_names)
        comps = detect_compositions(attrs, all_class_names)
        classes.append(
            {
                "name": cls.name,
                "module": mod,
                "bases": bases,
                "base_paths": base_paths,
                "stereotypes": st,
                "attributes": attrs,
                "methods": methods,
                "compositions": comps,
                "docstring": (ast.get_docstring(cls) or "").split("\n")[0][:200],
            }
        )

    # Inheritance edges limited to classes we actually found (internal edges),
    # plus a record of external bases (e.g. Exception, Data) for stereotype anchoring.
    internal = all_class_names
    inheritance = []
    external_bases = set()
    for c in classes:
        for b in c["bases"]:
            if b in internal:
                inheritance.append({"parent": b, "child": c["name"]})
            elif b not in ("object",):
                external_bases.add(b)

    graph = {
        "target": os.path.abspath(args.target),
        "class_count": len(classes),
        "classes": sorted(classes, key=lambda c: (c["module"], c["name"])),
        "inheritance": inheritance,
        "external_bases": sorted(external_bases),
        "modules": sorted({c["module"] for c in classes}),
    }

    out_json = json.dumps(graph, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_json)
        print(f"Wrote {graph['class_count']} classes across {len(graph['modules'])} modules -> {args.out}", file=sys.stderr)
    else:
        print(out_json)


if __name__ == "__main__":
    main()

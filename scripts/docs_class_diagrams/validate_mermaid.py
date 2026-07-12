#!/usr/bin/env python3
"""
Validate Mermaid classDiagram blocks extracted from a markdown file.

Two layers:
  1. If `mmdc` (@mermaid-js/mermaid-cli) is installed, render each block
     headless -- the authoritative check.
  2. Always run cheap structural lint that catches the mistakes LLMs actually
     make in classDiagram syntax, so the skill is useful even without Node.

Usage:
    python validate_mermaid.py <markdown-file>

Exit code 0 = all blocks OK, 1 = at least one problem (printed to stderr).
"""
import re
import shutil
import subprocess
import sys
import tempfile
import os


FENCE_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)

# valid relationship operators in mermaid class diagrams
REL_TOKENS = ["<|--", "--|>", "*--", "--*", "o--", "--o", "-->", "<--", "..>", "<..", "..|>", "--", ".."]


def find_blocks(md: str):
    return [m.group(1) for m in FENCE_RE.finditer(md)]


def lint_block(block: str, idx: int):
    problems = []
    lines = [l.rstrip() for l in block.splitlines()]
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        problems.append(f"block {idx}: empty")
        return problems
    if not non_empty[0].strip().startswith("classDiagram"):
        problems.append(f"block {idx}: does not start with 'classDiagram'")

    open_braces = block.count("{")
    close_braces = block.count("}")
    if open_braces != close_braces:
        problems.append(f"block {idx}: unbalanced braces ({open_braces} open, {close_braces} close)")

    declared = set(re.findall(r"class\s+([A-Za-z_]\w*)", block))

    # check relationship lines reference sane class tokens
    for ln in non_empty:
        s = ln.strip()
        if s.startswith("%%") or s.startswith("class ") or s.startswith("<<"):
            continue
        for tok in REL_TOKENS:
            if f" {tok} " in f" {s} ":
                # crude: split on the operator, ensure both sides have an identifier
                parts = re.split(re.escape(tok), s, maxsplit=1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].split(":")[0].strip()
                    for side in (left, right):
                        head = side.split()[0] if side.split() else ""
                        if head and not re.match(r"^[A-Za-z_]\w*$", head):
                            problems.append(
                                f"block {idx}: suspicious relationship operand '{side}' in line: {s}"
                            )
                break

    # stereotype syntax: <<abstract>> not <<abstract >> etc. (mermaid is lenient but flag empties)
    for ln in non_empty:
        if "<<" in ln and ">>" in ln:
            inner = ln[ln.find("<<") + 2 : ln.find(">>")].strip()
            if not inner:
                problems.append(f"block {idx}: empty stereotype <<>> in line: {ln.strip()}")

    return problems


def render_with_mmdc(block: str, idx: int):
    """Return list of problems from an actual mmdc render, or [] if OK."""
    with tempfile.TemporaryDirectory() as d:
        inp = os.path.join(d, f"b{idx}.mmd")
        outp = os.path.join(d, f"b{idx}.svg")
        with open(inp, "w") as f:
            f.write(block)
        try:
            res = subprocess.run(
                ["mmdc", "-i", inp, "-o", outp],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return [f"block {idx}: mmdc invocation failed: {e}"]
        if res.returncode != 0:
            err = (res.stderr or res.stdout).strip().splitlines()
            tail = " | ".join(err[-4:]) if err else "unknown error"
            return [f"block {idx}: mmdc render failed: {tail}"]
    return []


def main():
    if len(sys.argv) < 2:
        print("usage: validate_mermaid.py <markdown-file>", file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        md = f.read()

    blocks = find_blocks(md)
    if not blocks:
        print("No ```mermaid blocks found.", file=sys.stderr)
        sys.exit(1)

    have_mmdc = shutil.which("mmdc") is not None
    all_problems = []
    for i, b in enumerate(blocks, 1):
        all_problems.extend(lint_block(b, i))
        if have_mmdc:
            all_problems.extend(render_with_mmdc(b, i))

    mode = "mmdc + lint" if have_mmdc else "lint only (install @mermaid-js/mermaid-cli for full render check)"
    if all_problems:
        print(f"[{mode}] {len(blocks)} block(s), {len(all_problems)} problem(s):", file=sys.stderr)
        for p in all_problems:
            print("  - " + p, file=sys.stderr)
        sys.exit(1)
    print(f"[{mode}] {len(blocks)} block(s) OK.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan a Python *distribution* (pip name, e.g. 'ent_pycore') and produce
a catalog of the *actual importable packages/modules* it provides.

Outputs JSON and/or Markdown with:
- module → {functions/classes, signatures, first-line docs, file, line}
- metadata (distribution name, version, install location)

Usage:
  python scan_dist.py --dist ent_pycore --md out.md --json out.json
  python scan_dist.py --dist ent_pycore --ast  # AST mode (no imports)
"""

import argparse, os, sys, json, pkgutil, inspect, ast
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Iterable, Tuple

try:
    from importlib import metadata as md  # Python 3.8+
except Exception:
    print("Requires Python 3.8+ (importlib.metadata).", file=sys.stderr)
    sys.exit(1)

@dataclass
class Item:
    name: str
    kind: str   # "function" | "class"
    signature: str
    doc_head: str
    defined_in: Optional[str] = None
    line_no: Optional[int] = None

@dataclass
class ModuleReport:
    module: str
    error: Optional[str] = None
    items: List[Item] = None  # type: ignore

def read_top_level(dist: md.Distribution) -> List[str]:
    # Most wheels include this file; it lists import roots (one per line)
    try:
        text = dist.read_text("top_level.txt")
        if text:
            return [ln.strip() for ln in text.splitlines() if ln.strip()]
    except Exception:
        pass
    return []

def guess_top_level_from_files(dist: md.Distribution) -> List[str]:
    # Infer from .files list: any "pkg/__init__.py" or "mod.py" at top-level
    names = set()
    try:
        for f in dist.files or []:
            p = str(f)
            if p.endswith(".py") and ("/" not in p or p.count("/") == 1):
                # top-level module like "foo.py"
                if "/" not in p:
                    names.add(p[:-3])
                else:
                    head, tail = p.split("/", 1)
                    if tail == "__init__.py":
                        names.add(head)
    except Exception:
        pass
    return sorted(names)

def find_import_roots(dist_name: str) -> Tuple[md.Distribution, List[str]]:
    dist = md.distribution(dist_name)
    roots = read_top_level(dist)
    if not roots:
        roots = guess_top_level_from_files(dist)
    return dist, sorted(set(roots))

def should_keep(name: str, include_private: bool) -> bool:
    return include_private or not name.startswith("_")

def first_docline(s: Optional[str]) -> str:
    if not s:
        return ""
    lines = s.strip().splitlines()
    return " ".join(lines[:2]).strip()

def inspect_module(module, include_private: bool) -> List[Item]:
    out: List[Item] = []
    for n, obj in inspect.getmembers(module):
        if not should_keep(n, include_private):
            continue
        kind = None
        if inspect.isfunction(obj) or inspect.isbuiltin(obj):
            kind = "function"
        elif inspect.isclass(obj):
            kind = "class"
        if not kind:
            continue
        try:
            try:
                sig = str(inspect.signature(obj))
            except Exception:
                sig = "(signature unavailable)"
            try:
                srcfile = inspect.getsourcefile(obj) or inspect.getfile(obj)
            except Exception:
                srcfile = None
            try:
                _, lineno = inspect.getsourcelines(obj)
            except Exception:
                lineno = None
            out.append(Item(
                name=n, kind=kind, signature=sig,
                doc_head=first_docline(inspect.getdoc(obj)),
                defined_in=srcfile, line_no=lineno
            ))
        except Exception:
            continue
    return out

def walk_import(pkg_name: str, include_private: bool) -> List[ModuleReport]:
    reports: List[ModuleReport] = []
    try:
        root = __import__(pkg_name, fromlist=['*'])
        items = inspect_module(root, include_private)
        reports.append(ModuleReport(module=pkg_name, items=items))
    except Exception as e:
        reports.append(ModuleReport(module=pkg_name, error=repr(e), items=[]))
        return reports

    # Walk subpackages
    try:
        pkg_path = getattr(root, "__path__", None)
        if pkg_path:
            for finder, name, ispkg in pkgutil.walk_packages(pkg_path, prefix=pkg_name + "."):
                try:
                    mod = __import__(name, fromlist=['*'])
                    items = inspect_module(mod, include_private)
                    reports.append(ModuleReport(module=name, items=items))
                except Exception as e:
                    reports.append(ModuleReport(module=name, error=repr(e), items=[]))
    except Exception as e:
        reports.append(ModuleReport(module=pkg_name + ".__walk__", error=repr(e), items=[]))

    return reports

# -------- AST mode (no imports) --------
class AstVisitor(ast.NodeVisitor):
    def __init__(self, include_private: bool):
        self.include_private = include_private
        self.items: List[Item] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if should_keep(node.name, self.include_private):
            params = []
            a = node.args
            for p in a.args: params.append(p.arg)
            if a.vararg: params.append("*" + a.vararg.arg)
            for p in a.kwonlyargs: params.append(p.arg)
            if a.kwarg: params.append("**" + a.kwarg.arg)
            sig = "(" + ", ".join(params) + ")"
            doc = ast.get_docstring(node) or ""
            self.items.append(Item(
                name=node.name, kind="function", signature=sig,
                doc_head=first_docline(doc), line_no=getattr(node, "lineno", None)
            ))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if should_keep(node.name, self.include_private):
            doc = ast.get_docstring(node) or ""
            self.items.append(Item(
                name=node.name, kind="class",
                signature="(inspect via import for full signature)",
                doc_head=first_docline(doc), line_no=getattr(node, "lineno", None)
            ))
        self.generic_visit(node)

def package_dir(pkg_name: str) -> Optional[str]:
    try:
        mod = __import__(pkg_name, fromlist=['*'])
        path = getattr(mod, "__file__", None)
        if not path:  # namespace package
            # Try pkgutil to locate
            for m in pkgutil.iter_modules():
                if m.name == pkg_name:
                    return None
            return None
        return os.path.dirname(path)
    except Exception:
        return None

def walk_ast(pkg_name: str) -> List[ModuleReport]:
    base = package_dir(pkg_name)
    if base is None:
        # Could be a single-file module or a pure namespace package
        # Try to locate as a single .py in sys.path
        reports: List[ModuleReport] = []
        for p in sys.path:
            candidate = os.path.join(p, pkg_name + ".py")
            if os.path.isfile(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8") as fh:
                        src = fh.read()
                    tree = ast.parse(src, filename=candidate)
                    v = AstVisitor(args.include_private)
                    v.visit(tree)
                    for it in v.items: it.defined_in = candidate
                    reports.append(ModuleReport(module=pkg_name, items=v.items))
                except Exception as e:
                    reports.append(ModuleReport(module=pkg_name, error=repr(e), items=[]))
                return reports
        return [ModuleReport(module=pkg_name, error="Could not locate package directory", items=[])]
    reports: List[ModuleReport] = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for f in files:
            if not f.endswith(".py"): continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base)
            parts = [pkg_name] + rel[:-3].split(os.sep)
            if parts[-1] == "__init__": parts.pop()
            modname = ".".join(parts)
            try:
                with open(full, "r", encoding="utf-8") as fh:
                    src = fh.read()
                tree = ast.parse(src, filename=full)
                v = AstVisitor(args.include_private)
                v.visit(tree)
                for it in v.items: it.defined_in = full
                reports.append(ModuleReport(module=modname, items=v.items))
            except Exception as e:
                reports.append(ModuleReport(module=modname, error=repr(e), items=[]))
    return reports

def to_markdown(meta: Dict[str, str], reports: List[ModuleReport]) -> str:
    parts = []
    parts.append(f"# Distribution Catalog: `{meta.get('name','?')}`")
    parts.append("")
    parts.append(f"- **Version**: {meta.get('version','?')}  ")
    parts.append(f"- **Location**: {meta.get('location','?')}")
    parts.append("\n---\n")
    for rep in sorted(reports, key=lambda r: r.module):
        parts.append(f"## Module: `{rep.module}`")
        if rep.error:
            parts.append(f"> ❗ Error: `{rep.error}`\n")
            continue
        if not rep.items:
            parts.append("_No public functions/classes found._\n")
            continue
        parts.append("| Name | Kind | Signature | Doc (first line) | File | Line |")
        parts.append("|------|------|-----------|------------------|------|------|")
        for it in rep.items:
            sig = it.signature.replace("|", "\\|")
            doc = (it.doc_head or "").replace("|", "\\|")
            file_disp = (it.defined_in or "").replace("|", "\\|")
            line_disp = it.line_no if it.line_no is not None else ""
            parts.append(f"| `{it.name}` | {it.kind} | `{sig}` | {doc} | {file_disp} | {line_disp} |")
        parts.append("")
    return "\n".join(parts)

def scan_distribution(dist_name: str, ast_mode: bool, include_private: bool):
    dist, roots = find_import_roots(dist_name)
    meta = {
        "name": dist.metadata.get("Name", dist_name),
        "version": dist.version,
        "location": None,
        "roots": roots,
    }
    # locate install folder (best effort)
    try:
        # pick any file and get its parent
        files = list(dist.files or [])
        if files:
            anyfile = os.path.join(dist.locate_file(files[0]))
            meta["location"] = os.path.dirname(os.path.dirname(anyfile))  # site-packages
    except Exception:
        pass

    all_reports: List[ModuleReport] = []

    if not roots:
        # Nothing importable found
        all_reports.append(ModuleReport(
            module="(no top-level packages found)",
            error="Missing top_level.txt and could not infer import roots from files.",
            items=[]
        ))
        return meta, all_reports

    # Scan each discovered import root
    for root in roots:
        reports = walk_ast(root) if ast_mode else walk_import(root, include_private)
        all_reports.extend(reports)

    return meta, all_reports

def main(args):
    meta, reports = scan_distribution(args.dist, args.ast, args.include_private)

    out_json = {"meta": meta, "reports": [asdict(r) for r in reports]}
    json_text = json.dumps(out_json, indent=2)
    if not args.quiet:
        print(json_text)

    if args.md:
        md_text = to_markdown(meta, reports)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(md_text)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(json_text)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Scan a Python distribution (pip name) and catalog its importable modules.")
    p.add_argument("--dist", required=True, help="Distribution name (pip install name), e.g. ent_pycore")
    p.add_argument("--ast", action="store_true", help="Use AST mode (no imports, safer for heavy side-effects)")
    p.add_argument("--include-private", action="store_true", help="Include _private names")
    p.add_argument("--json", help="Write JSON here")
    p.add_argument("--md", help="Write Markdown here")
    p.add_argument("--quiet", action="store_true", help="Suppress JSON stdout")
    args = p.parse_args()
    main(args)

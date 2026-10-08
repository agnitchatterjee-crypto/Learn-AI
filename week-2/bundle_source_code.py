r"""Bundle every file under data/source into a single Markdown document.

Files are grouped by object type (the first-level folder: schemas, tables,
sequences, functions, procedures, views, constraints, seed). Within a type,
files are sorted by path, so sub-folders (e.g. tables/stg) stay together.

Usage:
    python bundle_source_code.py <base_folder> [--output <file.md>]

<base_folder> must be a fully qualified (absolute) path, e.g.
    python bundle_source_code.py "C:\projects\my-project\data\source"
If --output is omitted, "<base_folder_name>_source_code.md" is written to the
current working directory.
"""

import argparse
from datetime import datetime
from pathlib import Path

# Dependency-friendly order; unknown folders are appended alphabetically.
TYPE_ORDER = [
    "schemas",
    "sequences",
    "tables",
    "constraints",
    "views",
    "functions",
    "procedures",
    "seed",
]

# Markdown fence language by extension.
LANGS = {".sql": "sql", ".py": "python", ".json": "json", ".yaml": "yaml", ".yml": "yaml"}


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def fence_for(code: str) -> str:
    """Use a fence longer than any backtick run inside the code."""
    longest = run = 0
    for ch in code:
        run = run + 1 if ch == "`" else 0
        longest = max(longest, run)
    return "`" * max(3, longest + 1)


def group_by_type(source: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for f in sorted(p for p in source.rglob("*") if p.is_file()):
        rel = f.relative_to(source)
        obj_type = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        groups.setdefault(obj_type, []).append(f)

    ordered = [t for t in TYPE_ORDER if t in groups]
    ordered += sorted(t for t in groups if t not in TYPE_ORDER)
    return {t: groups[t] for t in ordered}


def anchor(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def build_markdown(source: Path) -> str:
    groups = group_by_type(source)
    total = sum(len(v) for v in groups.values())

    out = [
        "# Source Code Bundle",
        "",
        f"- **Source folder:** `{source}`",
        f"- **Generated:** {datetime.now():%Y-%m-%d %H:%M}",
        f"- **Total files:** {total}",
        "",
        "## Contents",
        "",
    ]
    for obj_type, files in groups.items():
        out.append(f"- [{obj_type.upper()}](#{anchor(obj_type)}) ({len(files)} files)")
    out.append("")

    for obj_type, files in groups.items():
        out += ["---", "", f"# {obj_type.upper()}", "", f"_{len(files)} file(s)_", ""]
        for f in files:
            rel = f.relative_to(source).as_posix()
            code = read_text(f).replace("\r\n", "\n").rstrip("\n")
            fence = fence_for(code)
            lang = LANGS.get(f.suffix.lower(), "")
            out += [f"## {f.name}", "", f"**Path:** `{rel}`", "", f"{fence}{lang}", code, fence, ""]

    return "\n".join(out)


def absolute_dir(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise argparse.ArgumentTypeError(f"base folder must be a fully qualified path: {value!r}")
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"base folder not found: {value!r}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base_folder", type=absolute_dir, help="fully qualified path of the folder to bundle")
    parser.add_argument("--output", type=Path, help="output .md path (default: ./<base_folder_name>_source_code.md)")
    args = parser.parse_args()

    output = args.output or Path.cwd() / f"{args.base_folder.name}_source_code.md"
    md = build_markdown(args.base_folder)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")
    print(f"Wrote {output} ({len(md):,} chars)")


if __name__ == "__main__":
    main()

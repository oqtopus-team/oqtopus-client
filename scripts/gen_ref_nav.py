"""Generate API reference pages and literate navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()
mod_symbol = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'

root = Path(__file__).parent.parent
src = root / "src"


def _is_excluded(parts: tuple[str, ...]) -> bool:
    """Return whether a module path should be excluded from generated reference.

    Returns:
        ``True`` when the module path should be skipped from the generated nav.

    """
    if not parts or parts[0] != "oqtopus_client":
        return True
    if parts[-1].startswith("_"):
        return True
    if len(parts) >= 3 and parts[1] == "rest":
        # Keep only oqtopus_client.rest (package root); exclude generated internals.
        if parts[2] != "__init__":
            return True
    return False


for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    parts = tuple(module_path.parts)
    if _is_excluded(parts):
        continue

    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")

    nav_parts = [f"{mod_symbol} {part}" for part in parts]
    nav[tuple(nav_parts)] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"---\ntitle: {ident}\n---\n\n::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, ".." / path.relative_to(root))

with mkdocs_gen_files.open("reference/API_reference.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

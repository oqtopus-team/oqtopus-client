"""Generate API reference pages and literate navigation."""

from os.path import relpath
from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()
mod_symbol = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'
REST_PACKAGE_DEPTH = 2
REST_PACKAGE = ("oqtopus_client", "rest")
REST_API_PACKAGE = (*REST_PACKAGE, "api")
REST_MODELS_PACKAGE = (*REST_PACKAGE, "models")

root = Path(__file__).parent.parent
src = root / "src"


def _is_excluded(parts: tuple[str, ...]) -> bool:
    """Return whether a module path should be excluded from generated reference.

    Returns:
        ``True`` when the module path should be skipped from the generated nav.

    """
    if not parts or parts[0] != "oqtopus_client":
        return True
    if parts[-1] == "__init__":
        return False
    return bool(parts[-1].startswith("_"))


def _reference_section(parts: tuple[str, ...]) -> tuple[str, str]:
    """Return the nav section label and output directory for a module path.

    Returns:
        A pair of ``(nav label, output directory)`` for the module.

    """
    if len(parts) >= REST_PACKAGE_DEPTH and parts[1] == "rest":
        return ("Generated OpenAPI Reference", "generated")
    return ("SDK Reference", "sdk")


def _should_generate_page(parts: tuple[str, ...]) -> bool:
    """Return whether a documentation page should be generated for a module.

    Returns:
        ``True`` when the module should get its own generated reference page.

    """
    return parts != ("oqtopus_client", "rest", "exceptions")


def _module_doc_link(parts: tuple[str, ...], section_dir: str) -> str:
    """Return the documentation path for a module.

    Returns:
        Documentation path relative to `reference/`.

    """
    package_dir = src.joinpath(*parts)
    is_package = package_dir.is_dir() and (package_dir / "__init__.py").exists()
    if parts[-1] == "__init__":
        doc_path = Path(*parts[:-1]) / "index.md"
    elif is_package:
        doc_path = Path(*parts) / "index.md"
    else:
        doc_path = Path(*parts).with_suffix(".md")
    return Path(section_dir, doc_path).as_posix()


def _iter_public_modules(
    package_dir: Path,
    package_parts: tuple[str, ...],
) -> list[tuple[str, tuple[str, ...]]]:
    """Return public modules directly under a package.

    Returns:
        A sorted list of ``(display label, module parts)``.

    """
    modules: list[tuple[str, tuple[str, ...]]] = []
    for path in sorted(package_dir.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        module_parts = (*package_parts, path.stem)
        modules.append((path.stem, module_parts))
    return modules


def _relative_doc_link(
    current_parts: tuple[str, ...],
    current_section_dir: str,
    target_parts: tuple[str, ...],
    target_section_dir: str,
) -> str:
    """Return a relative documentation link between generated pages.

    Returns:
        Relative markdown link path from one generated page to another.

    """
    current_link = _module_doc_link(current_parts, current_section_dir)
    target_link = _module_doc_link(target_parts, target_section_dir)
    current_doc = Path("reference", current_link)
    target_doc = Path("reference", target_link)
    return relpath(target_doc.as_posix(), start=current_doc.parent.as_posix())


def _render_bullet_links(
    modules: list[tuple[str, tuple[str, ...]]],
    section_dir: str,
    current_parts: tuple[str, ...],
) -> str:
    """Render markdown bullet links for module lists.

    Returns:
        Markdown list items pointing at generated reference pages.

    """
    return "".join(
        f"- [`{label}`]"
        f"({_relative_doc_link(current_parts, section_dir, parts, section_dir)})\n"
        for label, parts in modules
    )


def _custom_page_content(
    parts: tuple[str, ...],
    section_dir: str,
) -> str | None:
    """Return custom markdown content for special landing pages.

    Returns:
        Markdown page content when a special page should be generated.
        ``None`` when the page should use mkdocstrings output.

    """
    if tuple(parts) == REST_PACKAGE:
        api_modules = _iter_public_modules(
            src / "oqtopus_client" / "rest" / "api",
            REST_API_PACKAGE,
        )
        model_modules = _iter_public_modules(
            src / "oqtopus_client" / "rest" / "models",
            REST_MODELS_PACKAGE,
        )
        api_index_link = _relative_doc_link(
            parts,
            section_dir,
            (*REST_API_PACKAGE, "__init__"),
            section_dir,
        )
        models_index_link = _relative_doc_link(
            parts,
            section_dir,
            (*REST_MODELS_PACKAGE, "__init__"),
            section_dir,
        )
        api_client_link = _relative_doc_link(
            parts,
            section_dir,
            (*REST_PACKAGE, "api_client"),
            section_dir,
        )
        configuration_link = _relative_doc_link(
            parts,
            section_dir,
            (*REST_PACKAGE, "configuration"),
            section_dir,
        )
        api_response_link = _relative_doc_link(
            parts,
            section_dir,
            (*REST_PACKAGE, "api_response"),
            section_dir,
        )
        rest_transport_link = _relative_doc_link(
            parts,
            section_dir,
            (*REST_PACKAGE, "rest"),
            section_dir,
        )
        return (
            "---\ntitle: oqtopus_client.rest\n---\n\n"
            "# Generated OpenAPI Reference\n\n"
            "This section covers the low-level client generated from the OpenAPI "
            "schema. Start with the API classes when you want endpoint-oriented "
            "bindings, then move to the models for request and response types.\n\n"
            "## Main Entry Points\n\n"
            f"- [API Classes]({api_index_link})\n"
            f"- [Models]({models_index_link})\n"
            f"- [`api_client`]({api_client_link})\n"
            f"- [`configuration`]({configuration_link})\n"
            f"- [`api_response`]({api_response_link})\n"
            f"- [`rest`]({rest_transport_link})\n\n"
            "## API Classes\n\n"
            f"{_render_bullet_links(api_modules, section_dir, parts)}\n"
            "## Common Models\n\n"
            f"{_render_bullet_links(model_modules[:12], section_dir, parts)}"
        )

    if tuple(parts) == REST_API_PACKAGE:
        api_modules = _iter_public_modules(
            src / "oqtopus_client" / "rest" / "api",
            REST_API_PACKAGE,
        )
        return (
            "---\ntitle: oqtopus_client.rest.api\n---\n\n"
            "# API Classes\n\n"
            "Generated API classes grouped by endpoint family.\n\n"
            f"{_render_bullet_links(api_modules, section_dir, parts)}"
        )

    if tuple(parts) == REST_MODELS_PACKAGE:
        model_modules = _iter_public_modules(
            src / "oqtopus_client" / "rest" / "models",
            REST_MODELS_PACKAGE,
        )
        return (
            "---\ntitle: oqtopus_client.rest.models\n---\n\n"
            "# Models\n\n"
            "Generated request and response types used by the low-level OpenAPI "
            "client.\n\n"
            f"{_render_bullet_links(model_modules, section_dir, parts)}"
        )

    return None


for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    parts = tuple(module_path.parts)
    if _is_excluded(parts):
        continue
    if not _should_generate_page(parts):
        continue

    section_label, section_dir = _reference_section(parts)
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", section_dir, doc_path)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")

    nav_parts = [section_label, *[f"{mod_symbol} {part}" for part in parts]]
    nav[tuple(nav_parts)] = Path(section_dir, doc_path).as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        custom_content = _custom_page_content(parts, section_dir)
        if custom_content is not None:
            fd.write(custom_content)
        else:
            ident = ".".join(parts)
            fd.write(f"---\ntitle: {ident}\n---\n\n::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, ".." / path.relative_to(root))

with mkdocs_gen_files.open("reference/index.md", "w") as overview_file:
    overview_file.write(
        "# API Reference\n\n"
        "The API reference includes both the hand-written SDK surface and the "
        "OpenAPI-generated client/types.\n\n"
        "- [SDK Reference](sdk/oqtopus_client/index.md): public helpers such as "
        "`OqtopusClient`, `OqtopusConfig`, job specs, and typed results.\n"
        "- [Generated OpenAPI Reference](generated/oqtopus_client/rest/index.md): "
        "generated API classes, low-level REST client utilities, and OpenAPI "
        "models under `oqtopus_client.rest`.\n"
    )

with mkdocs_gen_files.open("reference/API_reference.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

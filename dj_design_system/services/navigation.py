"""
Navigation tree builder for the component gallery.

Builds a nested tree structure from the component registry and filesystem
markdown files, suitable for rendering a hierarchical sidebar navigation.

The tree reflects the source-code directory structure under each app's
``components/`` package, with two convenience rules:

1. The leaf-most folder is **collapsed** when its name matches the component
   name (e.g. ``elements/icon/component.py`` appears as *Icon* inside
   *Elements*, not *Elements → Icon → Icon*).
2. ``index.md`` files (case-insensitive) are attached to their parent folder
   node rather than appearing as separate entries; all other ``.md`` files
   become standalone document nodes.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING

import markdown as markdown_lib
from django.urls import reverse

from dj_design_system.data import NavNode
from dj_design_system.types import NodeType


if TYPE_CHECKING:
    from dj_design_system.data import ComponentInfo


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def to_display_label(
    name: str,
    *,
    component: ComponentInfo | None = None,
    app_label: str | None = None,
) -> str:
    """Return a human-readable label for a slug, component, or app.

    Resolution order:

    1. If *component* is given, its ``Meta.verbose_name`` is used when present.
    2. If *app_label* is given, the corresponding ``AppConfig.verbose_name``
       is used when it was **explicitly declared** on the config class
       (Django's auto-generated value is ignored).
    3. Falls back to converting *name* from snake_case / kebab-case to
       sentence case.

    Examples::

        >>> to_display_label("icon")
        'Icon'
        >>> to_display_label("info_card")
        'Info card'
        >>> to_display_label("hero-banner")
        'Hero banner'
    """
    if component is not None:
        meta = component.component_class.__dict__.get("Meta")
        if meta is not None:
            vn = getattr(meta, "verbose_name", None)
            if isinstance(vn, str):
                return vn

    if app_label is not None:
        from django.apps import apps

        try:
            cfg = apps.get_app_config(app_label)
        except LookupError:
            pass
        else:
            if "verbose_name" in type(cfg).__dict__:
                return str(cfg.verbose_name)

    return name.replace("_", " ").replace("-", " ").capitalize()


# ---------------------------------------------------------------------------
# Tree construction
# ---------------------------------------------------------------------------


def _effective_path_parts(info: ComponentInfo) -> list[str]:
    """Return directory segments for a component, applying the collapsing rule.

    If the deepest folder name equals the component name, that folder is
    dropped so the component is placed one level higher in the tree.
    """
    parts = info.relative_path.split(".") if info.relative_path else []
    if parts and parts[-1] == info.name:
        parts = parts[:-1]
    return parts


class _AppTreeBuilder:
    """Builds the navigation subtree for a single app.

    Maintains a path-keyed index of nodes so that repeated references to the
    same folder (e.g. from multiple components or markdown files) reuse the
    same ``NavNode`` rather than creating duplicates.

    Paths in the index use ``"/"`` as delimiter (e.g. ``"elements/cards"``).
    """

    def __init__(self, app_node: NavNode):
        self.root = app_node
        self._nodes_by_path: dict[str, NavNode] = {}

    # -- folder resolution -------------------------------------------------

    def get_or_create_folder(self, path_parts: list[str]) -> NavNode:
        """Return the node at *path_parts*, creating intermediate folders as needed."""
        current = self.root
        for depth in range(len(path_parts)):
            path_key = "/".join(path_parts[: depth + 1])
            if path_key not in self._nodes_by_path:
                node = NavNode(
                    label=to_display_label(path_parts[depth]),
                    slug=path_parts[depth],
                    node_type=NodeType.FOLDER,
                )
                current.children.append(node)
                self._nodes_by_path[path_key] = node
            current = self._nodes_by_path[path_key]
        return current

    # -- components --------------------------------------------------------

    def add_component(self, info: ComponentInfo) -> None:
        """Add a component to the tree, applying the leaf-folder collapsing rule.

        When the deepest folder name matches the component name, the folder
        is collapsed and the component is placed one level higher.  If that
        collapsed folder already exists as a node, it is upgraded in-place.
        """
        collapsed_parts = _effective_path_parts(info)
        raw_parts = info.relative_path.split(".") if info.relative_path else []
        is_collapsed = len(raw_parts) > len(collapsed_parts)

        parent = self.get_or_create_folder(collapsed_parts)

        if is_collapsed:
            raw_path = "/".join(raw_parts)
            if raw_path in self._nodes_by_path:
                existing = self._nodes_by_path[raw_path]
                existing.upgrade_to_component(
                    info, to_display_label(info.name, component=info)
                )
                return

        node = NavNode(
            label=to_display_label(info.name, component=info),
            slug=info.name,
            node_type=NodeType.COMPONENT,
            component=info,
        )
        parent.children.append(node)

        # Register under the original (un-collapsed) path so markdown
        # discovery for sibling files (e.g. icon/index.md) finds this
        # node rather than creating a duplicate.
        if is_collapsed:
            self._nodes_by_path["/".join(raw_parts)] = node

    # -- markdown ----------------------------------------------------------

    def add_markdown(self, dir_parts: list[str], md_path: Path) -> None:
        """Add a markdown file to the tree.

        ``index.md`` (case-insensitive) is attached to its containing
        folder node.  All other ``.md`` files become document leaf nodes.
        """
        parent = self.get_or_create_folder(dir_parts)

        if md_path.name.lower() == "index.md":
            parent.index_doc_path = md_path
        else:
            stem = md_path.stem
            node = NavNode(
                label=to_display_label(stem),
                slug=stem,
                node_type=NodeType.DOCUMENT,
                doc_path=md_path,
            )
            parent.children.append(node)


def _discover_markdown_files(components_root: Path) -> list[tuple[list[str], Path]]:
    """Walk *components_root* for ``.md`` files.

    Returns a list of ``(relative_dir_parts, file_path)`` tuples.
    """
    results: list[tuple[list[str], Path]] = []
    if not components_root.is_dir():
        return results

    for path in sorted(components_root.rglob("*")):
        if path.is_file() and path.suffix.lower() == ".md":
            relative = path.relative_to(components_root)
            dir_parts = list(relative.parent.parts)
            results.append((dir_parts, path))

    return results


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


def _sort_children(node: NavNode) -> None:
    """Recursively sort children by the configured type order, then alphabetically."""

    from dj_design_system.settings import dds_settings

    nav_order = dds_settings.GALLERY_NAV_ORDER

    def _sort_key(child: NavNode) -> tuple[int, str]:
        if not isinstance(nav_order, list):
            return (0, child.label.lower())

        rank = {nt: i for i, nt in enumerate(nav_order)}
        return (rank.get(child.node_type, len(nav_order)), child.label.lower())

    node.children.sort(key=_sort_key)
    for child in node.children:
        _sort_children(child)


def _annotate_paths(
    node: NavNode,
    app_label: str = "",
    parent_parts: list[str] | None = None,
) -> None:
    """Recursively set ``_app_label`` and ``_path_parts`` on every node.

    This enables ``NavNode.url`` and ``NavNode.active_path`` to work.
    """
    if parent_parts is None:
        parent_parts = []

    node._app_label = app_label
    if node.node_type == NodeType.APP:
        node._path_parts = []
        child_app = node.slug
        child_parts: list[str] = []
    else:
        node._path_parts = parent_parts + [node.slug]
        child_app = app_label
        child_parts = node._path_parts

    for child in node.children:
        _annotate_paths(child, app_label=child_app, parent_parts=child_parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_navigation() -> list[NavNode]:
    """Build the full gallery navigation tree from the component registry and markdown files.

    Can be cleaned up when we are able to test without being inside intranet repo/having clash with the real component registry by making the registry an explicit parameter and doing markdown discovery outside this function, but for now this is easier to work with.
    """
    return _build_navigation()


def _build_navigation(
    components: list[ComponentInfo] | None = None,
    app_component_paths: dict[str, Path] | None = None,
) -> list[NavNode]:
    """Build the full gallery navigation tree.

    When called with no arguments (the production path), components are
    read from the global :data:`component_registry` and markdown files
    are discovered from every installed app's ``components/`` directory.

    Both parameters are exposed for tests that supply synthetic data.

    Parameters
    ----------
    components:
        Component list to build the tree from.  Defaults to
        ``component_registry.list_all()``.
    app_component_paths:
        Mapping of ``app_label`` → filesystem ``Path`` to the app's
        ``components/`` directory for markdown discovery.  Defaults to
        auto-discovery via :func:`get_app_component_paths` when
        *components* is also ``None``; otherwise defaults to no
        discovery (empty dict) so that tests passing synthetic
        components don't pick up unrelated real apps.

    Returns
    -------
    list[NavNode]
        A list of top-level app nodes, sorted alphabetically, each
        containing a nested tree of folders, components, and documents.
    """
    if components is None:
        from dj_design_system.services.registry import component_registry

        components = component_registry.list_all()
        if app_component_paths is None:
            app_component_paths = get_app_component_paths()

    if app_component_paths is None:
        app_component_paths = {}

    apps: dict[str, list[ComponentInfo]] = {}
    for info in components:
        apps.setdefault(info.app_label, []).append(info)

    # Ensure apps with only markdown (no components) also appear.
    for app_label, _path in app_component_paths.items():
        if app_label not in apps:
            apps[app_label] = []

    result: list[NavNode] = []
    for app_label in sorted(apps):
        app_node = NavNode(
            label=to_display_label(app_label, app_label=app_label),
            slug=app_label,
            node_type=NodeType.APP,
        )

        builder = _AppTreeBuilder(app_node)

        for info in apps[app_label]:
            builder.add_component(info)

        if app_label in app_component_paths:
            for dir_parts, md_path in _discover_markdown_files(
                app_component_paths[app_label]
            ):
                builder.add_markdown(dir_parts, md_path)

        _sort_children(app_node)
        _annotate_paths(app_node)
        result.append(app_node)

    return result


def get_app_component_paths() -> dict[str, Path]:
    """Look up the ``components/`` directory for every installed Django app.

    Returns a dict of ``{app_label: Path}`` for apps that have a
    ``components/`` directory (either a package or a single module file is
    accepted, but only packages will yield markdown discovery results).
    """
    from django.apps import apps

    paths: dict[str, Path] = {}
    for app_config in apps.get_app_configs():
        components_dir = Path(app_config.path) / "components"
        if components_dir.is_dir():
            paths[app_config.label] = components_dir
    return paths


def find_node(
    nav_tree: list[NavNode],
    app_label: str,
    path_parts: list[str],
) -> NavNode | None:
    """Walk the navigation tree to find a node by app_label and path segments."""
    app_node = None
    for node in nav_tree:
        if node.slug == app_label:
            app_node = node
            break
    if app_node is None:
        return None

    current = app_node
    for part in path_parts:
        child = None
        for c in current.children:
            if c.slug == part:
                child = c
                break
        if child is None:
            return None
        current = child
    return current


class _HTMLTextExtractor(HTMLParser):
    """Accumulates visible text from an HTML string, ignoring all tags."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        """Collect each text node."""
        self._parts.append(data)

    def get_text(self) -> str:
        """Return all collected text joined with spaces."""
        return " ".join(self._parts)


def strip_markdown(text: str) -> str:
    """Convert markdown to plain text for search indexing.

    Renders the markdown to HTML using the ``markdown`` package, then
    strips all tags via the stdlib ``HTMLParser`` to produce clean plain
    text suitable for full-text matching.
    """
    html_content = markdown_lib.markdown(text, extensions=["fenced_code", "tables"])
    extractor = _HTMLTextExtractor()
    extractor.feed(html_content)
    return " ".join(extractor.get_text().split())


def _collect_search_entries(
    node: NavNode,
    ancestor_labels: list[str],
    entries: list[dict],
) -> None:
    """Recursively walk the nav tree and append one search entry per node.

    APP nodes are skipped (they are grouping containers, not navigable
    destinations in a meaningful way). All other node types produce an entry
    with the following fields:

    - ``label``: human-readable title of the node
    - ``url``: absolute URL path for the node
    - ``type``: node type string (``"component"``, ``"document"``, ``"folder"``)
    - ``breadcrumb``: ancestor labels joined with " / " for display context
    - ``content``: plain-text body for full-text matching
    """
    if node.node_type == NodeType.APP:
        for child in node.children:
            _collect_search_entries(child, [node.label], entries)
        return

    breadcrumb = " / ".join(ancestor_labels)

    content_parts: list[str] = []
    if node.is_component and node.component is not None:
        doc = (node.component.component_class.__doc__ or "").strip()
        if doc:
            content_parts.append(strip_markdown(doc))
    if node.has_index_doc and node.index_doc_path is not None:
        try:
            raw = node.index_doc_path.read_text(encoding="utf-8")
            content_parts.append(strip_markdown(raw))
        except OSError:
            pass
    if node.is_document and node.doc_path is not None:
        try:
            raw = node.doc_path.read_text(encoding="utf-8")
            content_parts.append(strip_markdown(raw))
        except OSError:
            pass

    entries.append(
        {
            "label": node.label,
            "url": node.url,
            "type": node.node_type.value,
            "breadcrumb": breadcrumb,
            "content": " ".join(content_parts),
        }
    )

    child_ancestors = ancestor_labels + [node.label]
    for child in node.children:
        _collect_search_entries(child, child_ancestors, entries)


def build_search_index(nav_tree: list[NavNode]) -> list[dict]:
    """Build a flat list of search index entries from the navigation tree.

    Each entry is a dict suitable for JSON serialisation:

    - ``label``: human-readable title
    - ``url``: absolute URL path
    - ``type``: ``"component"``, ``"document"``, or ``"folder"``
    - ``breadcrumb``: ancestor labels joined with " / "
    - ``content``: plain-text body (docstring or markdown), used for full-text search

    APP nodes (top-level grouping containers) are omitted from the results.
    """
    entries: list[dict] = []
    for app_node in nav_tree:
        _collect_search_entries(app_node, [], entries)
    return entries


def build_breadcrumbs(
    app_label: str,
    path_parts: list[str],
    current_label: str,
) -> list[dict]:
    """Build breadcrumb trail for the current page.

    Each entry has ``label`` and ``url`` (except the last which has no url).
    """
    crumbs = [{"label": "Gallery", "url": reverse("gallery")}]
    crumbs.append(
        {
            "label": to_display_label(app_label, app_label=app_label),
            "url": reverse("gallery-node-root", kwargs={"app_label": app_label}),
        }
    )

    accumulated = []
    for part in path_parts:
        accumulated.append(part)
        crumbs.append(
            {
                "label": to_display_label(part),
                "url": reverse(
                    "gallery-node",
                    kwargs={"app_label": app_label, "path": "/".join(accumulated)},
                ),
            }
        )

    # Last crumb is the current page (no link)
    crumbs.append({"label": current_label})
    return crumbs

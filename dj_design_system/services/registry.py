import inspect
import pkgutil
from importlib import import_module
from pathlib import Path
from typing import Type

from dj_design_system.data import ComponentInfo, ComponentMedia
from dj_design_system.services.component import (
    derive_name,
    derive_relative_path,
    get_meta_name,
    is_abstract,
)
from dj_design_system.types import TagType


class ComponentDoesNotExist(Exception):
    """Raised when a component lookup finds no matching component."""


class MultipleComponentsFound(Exception):
    """Raised when a component lookup finds multiple matching components."""


class ComponentRegistry:
    """
    A central registry for design-system components.

    Components are auto-discovered at startup by importing each installed
    app's ``components`` module or package — mirroring the way Django
    discovers ``admin`` modules.

    In any installed app, create a ``components.py`` file or a ``components/``
    package containing Python files that define ``BaseComponent`` subclasses::

        # myapp/components/button.py
        from dj_design_system.components import BaseComponent

        class ButtonComponent(BaseComponent):
            ...

    Components are discovered automatically. To opt out, set
    ``abstract = True`` on an inner ``Meta`` class::

        class AbstractCard(BaseComponent):
            class Meta:
                abstract = True

    To set a custom name (used for lookups via ``get_by_name``)::

        class HeroCardComponent(BaseComponent):
            class Meta:
                name = "hero"
    """

    COMPONENTS_MODULE = "components"

    def __init__(self) -> None:
        self._components: list[ComponentInfo] = []

    def autodiscover(self) -> None:
        """
        Import the ``components`` module or package from every installed
        Django app and register all discovered ``BaseComponent`` subclasses.

        Called automatically from ``DjangoDesignSystemConfig.ready()``.
        """
        from django.apps import apps

        for app_config in apps.get_app_configs():
            module_path = f"{app_config.name}.{self.COMPONENTS_MODULE}"
            try:
                module = import_module(module_path)
            except ImportError:
                # App has no components module — that's fine.
                continue
            except Exception as exc:
                raise ImportError(
                    f"Error importing components from '{module_path}': {exc}"
                ) from exc

            self._discover_module(module, app_config.label, relative_path="")

            for submodule, relative_path in self._iter_app_submodules(
                module, module_path
            ):
                self._discover_module(submodule, app_config.label, relative_path)

    def _iter_app_submodules(self, module, module_path: str):
        """
        Yield ``(submodule, relative_path)`` for every module in a components package.

        Only applies when ``module`` is a package (i.e. has a ``__path__``).
        ``relative_path`` is the dotted directory path relative to the
        ``components`` package root.
        """
        if not hasattr(module, "__path__"):
            return

        for _importer, modname, _ispkg in pkgutil.walk_packages(
            module.__path__, prefix=module.__name__ + "."
        ):
            try:
                submodule = import_module(modname)
            except Exception as exc:
                raise ImportError(f"Error importing '{modname}': {exc}") from exc

            yield submodule, derive_relative_path(modname, module_path)

    def _discover_module(self, module, app_label: str, relative_path: str) -> None:
        """
        Inspect a module for BaseComponent subclasses and register them.

        Skips abstract components, imported classes (not defined in this
        module), and the base classes themselves.
        """
        from dj_design_system.components import (
            BlockComponent,
            TagComponent,
        )

        concrete_components = (
            obj
            for _attr_name, obj in inspect.getmembers(module, inspect.isclass)
            if issubclass(obj, (TagComponent, BlockComponent))
            and not is_abstract(obj)
            and obj.__module__ == module.__name__
        )

        for obj in concrete_components:
            info = ComponentInfo(
                component_class=obj,
                name=get_meta_name(obj) or derive_name(obj),
                app_label=app_label,
                relative_path=relative_path,
            )
            self._bind_template(info)
            self._components.append(info)

    def _bind_template(self, info: ComponentInfo) -> None:
        """
        Resolve and validate the template source for *info*'s component class.

        Checks for three template sources (in priority order):

        1. **Explicit ``template_name``** — a ``template_name`` attribute
           defined directly on the class, pointing at any template the
           loader chain can find.
        2. **Co-located HTML file** — a ``{name}.html`` file sitting next
           to the component's ``.py`` source file.
        3. **``template_format_str``** — the existing Python-format-string
           fallback (current default behaviour).

        Raises ``ImproperlyConfigured`` if both a ``template_format_str``
        (defined directly on the class, not inherited) **and** an HTML-based
        template (``template_name`` or co-located file) are present — these
        two approaches cannot coexist on the same component class.

        When an HTML template is resolved, sets ``cls._template_name`` so
        that ``render()`` can find it without repeating filesystem I/O.
        """
        from django.core.exceptions import ImproperlyConfigured

        from dj_design_system.services.media import build_static_url

        cls = info.component_class
        has_format_str = "template_format_str" in cls.__dict__
        has_explicit_template = "template_name" in cls.__dict__

        # Check for a co-located .html file next to the component source.
        colocated_template_name: str | None = None
        try:
            source_file = inspect.getfile(cls)
        except (TypeError, OSError):
            pass
        else:
            source_dir = Path(source_file).parent
            if (source_dir / f"{info.name}.html").is_file():
                colocated_template_name = build_static_url(
                    info.app_label, info.relative_path, info.name, ".html"
                )

        has_html_template = has_explicit_template or colocated_template_name is not None

        if has_format_str and has_html_template:
            if has_explicit_template:
                conflict = "'template_name'"
            else:
                conflict = f"a co-located HTML template ('{info.name}.html')"
            raise ImproperlyConfigured(
                f"Component '{cls.__name__}' defines both 'template_format_str' "
                f"and {conflict}. Use one or the other."
            )

        if has_explicit_template:
            cls._template_name = cls.template_name  # type: ignore[attr-defined]
        elif colocated_template_name is not None:
            cls._template_name = colocated_template_name

    # ------------------------------------------------------------------
    # Lookup methods
    # ------------------------------------------------------------------

    def list_all(self) -> list[ComponentInfo]:
        """Return all discovered components."""
        return list(self._components)

    def get_merged_media(self) -> ComponentMedia:
        """Return a single ``ComponentMedia`` merging all registered components."""
        result = ComponentMedia()
        for info in self._components:
            result = result.merge(info.media)
        return result

    def list_by_app(self, app_label: str) -> list[ComponentInfo]:
        """Return all components belonging to the given app."""
        return [c for c in self._components if c.app_label == app_label]

    def get_by_name(self, name: str, app_label: str | None = None) -> ComponentInfo:
        """
        Look up a component by its name.

        If ``app_label`` is provided, the search is scoped to that app.
        Raises ``ComponentDoesNotExist`` if no match is found, and
        ``MultipleComponentsFound`` if the name is ambiguous.
        """
        candidates = self._components
        if app_label is not None:
            candidates = self.list_by_app(app_label)

        matches = [c for c in candidates if c.name == name]

        if len(matches) == 0:
            if app_label:
                raise ComponentDoesNotExist(
                    f"No component named '{name}' found in app '{app_label}'."
                )
            raise ComponentDoesNotExist(f"No component named '{name}' found.")

        if len(matches) > 1:
            apps = sorted({c.app_label for c in matches})
            raise MultipleComponentsFound(
                f"Multiple components named '{name}' found in apps: "
                f"{', '.join(apps)}. Use get_by_name('{name}', "
                f"app_label='...') to disambiguate."
            )

        return matches[0]

    def get_info(self, component_class: Type) -> ComponentInfo:
        """
        Look up the ``ComponentInfo`` for a given component class.

        Raises ``ComponentDoesNotExist`` if the class is not registered.
        """
        for info in self._components:
            if info.component_class is component_class:
                return info
        raise ComponentDoesNotExist(
            f"Component class '{component_class.__name__}' is not registered."
        )

    # ------------------------------------------------------------------
    # Template tag registration
    # ------------------------------------------------------------------

    def register_templatetags(
        self,
        library: "django.template.Library",  # type: ignore[name-defined]  # noqa: F821
        app_label: str | None = None,
    ) -> None:
        """Register discovered components as template tags on a Django Library.

        For each component with a ``tag_type``:

        * Always registers the component with its ``qualified_name``
          (e.g. ``fake_app__cards__hero``).
        * Also registers with the short ``name``. When multiple components
          share the same short name, the **last one discovered wins** — i.e.
          the one from the app that appears latest in ``INSTALLED_APPS``.
          This allows apps to intentionally override components from earlier
          apps.

        Args:
            library: A ``django.template.Library`` instance to register on.
            app_label: When provided, only components from this app are
                registered and uniqueness is scoped to this app.
        """
        candidates = self._components
        if app_label is not None:
            candidates = self.list_by_app(app_label)

        short_names: dict[str, ComponentInfo] = {}
        for info in candidates:
            # Always register with qualified name
            self._register_tag(library, info.qualified_name, info)

            # Register short names — last discovered wins
            short_names[info.name] = info

        for name, info in short_names.items():
            self._register_tag(library, name, info)

    @staticmethod
    def _register_tag(
        library: "django.template.Library",  # type: ignore[name-defined]  # noqa: F821
        tag_name: str,
        info: "ComponentInfo",
    ) -> None:
        """Register a single component on a library with the given name."""
        if info.tag_type is TagType.BLOCK and info.component_class.has_slots():
            # Slotted block components use a custom compilation function
            from dj_design_system.services.slot_node import make_slotted_block_tag

            compilation_func = make_slotted_block_tag(info.component_class, tag_name)
            library.tag(tag_name, compilation_func)
            return

        tag_func = info.component_class.as_tag()
        if info.tag_type is TagType.BLOCK:
            library.simple_block_tag(name=tag_name)(tag_func)
            return

        library.simple_tag(name=tag_name)(tag_func)


# Module-level singleton
component_registry = ComponentRegistry()

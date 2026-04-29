from typing import TYPE_CHECKING, Any

from django.utils.html import format_html
from django.utils.safestring import SafeString

from dj_design_system.parameters import BaseParam


if TYPE_CHECKING:
    from dj_design_system.data import ComponentMedia


class BaseComponent:
    # The template string itself to pass to format_html. Should be overridden by subclasses.
    template_format_str: str = "<span class='{classes}'>ABSTRACT COMPONENT</span>"

    class Meta:
        abstract = True

    def __init_subclass__(cls, **kwargs) -> None:
        """Validate Meta constraint declarations at class definition time."""
        super().__init_subclass__(**kwargs)
        from dj_design_system.services.component import get_own_meta, is_abstract

        if is_abstract(cls):
            return

        meta = get_own_meta(cls)
        param_names = set(cls.get_params().keys())

        for a, b in getattr(meta, "mutually_exclusive", []):
            for name in (a, b):
                if name not in param_names:
                    raise ValueError(
                        f"{cls.__name__}.Meta.mutually_exclusive references unknown param '{name}'."
                    )

        for dependent, dependency in getattr(meta, "requires", []):
            for name in (dependent, dependency):
                if name not in param_names:
                    raise ValueError(
                        f"{cls.__name__}.Meta.requires references unknown param '{name}'."
                    )

    def __init__(self, **kwargs):
        self.context = {}
        for var_name, var_value in kwargs.items():
            setattr(self, var_name, var_value)

        self._validate_meta_constraints()
        self.validate_params()

    def validate_params(self) -> None:
        """An override hook allowing param combinations or values to raise exceptions if necessary"""
        ...

    def _validate_meta_constraints(self) -> None:
        """Enforce mutually_exclusive and requires constraints declared on Meta.

        Called automatically during __init__ before validate_params.
        - Meta.mutually_exclusive: list of (param_a, param_b) pairs that cannot both be set.
        - Meta.requires: list of (dependent, dependency) pairs where setting dependent
          requires dependency to also be set.
        """
        from dj_design_system.services.component import get_own_meta

        params = type(self).get_params()
        meta = get_own_meta(type(self))

        for a, b in getattr(meta, "mutually_exclusive", []):
            if params[a].has_been_set(self) and params[b].has_been_set(self):
                raise ValueError(
                    f"'{a}' and '{b}' cannot both be set on {type(self).__name__}."
                )

        for dependent, dependency in getattr(meta, "requires", []):
            if params[dependent].has_been_set(self) and not params[
                dependency
            ].has_been_set(self):
                raise ValueError(
                    f"'{dependent}' requires '{dependency}' to also be set on {type(self).__name__}."
                )

    def get_context(self) -> dict[str, Any]:
        """
        Get the context for rendering the component. This method can be overridden by subclasses to add additional or edit other context variables.
        """
        self.context["classes"] = self.get_classes_string()
        for param_name, spec in self.params.items():
            value = getattr(self, param_name)
            self.context[param_name] = value
            self.context.update(spec.get_extra_context(param_name, value))
        return self.context

    def get_classes_string(self):
        """
        Get a string of CSS classes based on the context. This can be used in the template to apply conditional styling.
        """
        classes = []
        for param_name, spec in self.params.items():
            param_value = getattr(self, param_name)
            classes.extend(spec.get_css_classes(param_name, param_value))
        return " ".join(classes)

    def render(self) -> str:
        """
        Render the component as an HTML string.
        """
        return format_html(format_string=self.template_format_str, **self.get_context())

    def __str__(self) -> str:
        return self.render()

    def __html__(self) -> str:
        return self.render()

    @property
    def description(self) -> str | None:
        return self.__doc__

    @property
    def params(self) -> dict[str, "BaseParam"]:
        return type(self).get_params()

    @classmethod
    def get_params(cls) -> dict[str, "BaseParam"]:
        """
        Get the parameters for this component. Returns a dictionary of all
        BaseParam descriptors defined on the class (or any subclass in the MRO).
        """
        result = {}
        for klass in cls.__mro__:
            for attr_name, attr_value in vars(klass).items():
                if isinstance(attr_value, BaseParam) and attr_name not in result:
                    result[attr_name] = attr_value
        return result

    @classmethod
    def docstring(cls) -> str:
        """
        Return a string describing the API of this component, including its parameters and their types.
        """
        params = cls.get_params()
        api_docs = f"{cls.__doc__}\n\n"
        if len(params) > 0:
            api_docs += "Parameters:\n"
        for parameter_spec in params.values():
            api_docs += f"- {parameter_spec.docstring()}\n"
        return api_docs

    @classmethod
    def get_name(cls) -> str:
        """Return the component's registered name from the registry."""
        from dj_design_system import component_registry

        return component_registry.get_info(cls).name

    @classmethod
    def get_app_label(cls) -> str:
        """Return the app label this component was discovered in."""
        from dj_design_system import component_registry

        return component_registry.get_info(cls).app_label

    @classmethod
    def get_relative_path(cls) -> str:
        """Return the relative path within the app's components directory."""
        from dj_design_system import component_registry

        return component_registry.get_info(cls).relative_path

    @classmethod
    def get_media(cls) -> "ComponentMedia":
        """Return the CSS and JS static URL paths required by this component.

        Delegates to ``ComponentInfo.media`` — see that property for full
        documentation of auto-discovery and ``Media`` class override behaviour.
        """
        from dj_design_system import component_registry

        return component_registry.get_info(cls).media

    @classmethod
    def get_positional_args(cls) -> list[str]:
        """Return the list of positional arg names from the class's own Meta.positional_args.

        Only looks at the class's own ``Meta`` — positional_args are NOT
        inherited from parent classes, matching Django's convention that
        Meta is not inherited. This avoids silent ordering surprises when
        subclassing.
        """
        from dj_design_system.services.component import get_own_meta

        meta = get_own_meta(cls)
        positional = getattr(meta, "positional_args", None)
        return list(positional) if positional else []

    @staticmethod
    def map_positional_args(
        positional_args: list[str], args: tuple, kwargs: dict
    ) -> dict:
        """Map positional arguments to keyword arguments using the positional_args spec."""
        for i, arg_name in enumerate(positional_args):
            if i < len(args):
                kwargs[arg_name] = args[i]
        return kwargs


class TagComponent(BaseComponent):
    """
    A component registered as a Django ``simple_tag``.

    Subclass this for components that produce a single HTML fragment
    without wrapping nested template content.

    Use ``Meta.positional_args`` to declare parameters that can be passed
    as positional arguments in the template tag::

        class IconComponent(TagComponent):
            name = StrParam("The icon name.")

            class Meta:
                positional_args = ["name"]

    This allows ``{% icon "check" %}`` instead of ``{% icon name="check" %}``.
    """

    class Meta:
        abstract = True

    @classmethod
    def as_tag(cls):
        """Return a template tag function mapping positional args via Meta.positional_args."""
        positional_args = cls.get_positional_args()

        def _tag(*args, **kwargs):
            cls.map_positional_args(positional_args, args, kwargs)
            return cls(**kwargs)

        return _tag


class BlockComponent(BaseComponent):
    """
    A component registered as a Django ``simple_block_tag``, allowing
    for nested template content.

    The template should include a ``{content}`` placeholder where the
    inner content will be rendered. ``content`` is always the first
    positional argument and should NOT appear in ``Meta.positional_args``.

    Use ``Meta.positional_args`` to declare additional positional args
    beyond ``content``::

        class SectionComponent(BlockComponent):
            title = StrParam("Section title.")

            class Meta:
                positional_args = ["title"]

    This allows ``{% section "My Title" %}...{% endsection %}``.
    """

    class Meta:
        abstract = True

    template_format_str: str = "<span class='{classes}'>{content}</span>"

    def __init__(self, content: SafeString, **kwargs):
        self.content = content
        super().__init__(**kwargs)

    def get_context(self) -> dict[str, Any]:
        """Add ``content`` to the context automatically.

        ``content`` is the block body passed by the template engine — it is
        NOT a declared BaseParam and should not appear in ``Meta.positional_args``
        or ``docstring()`` output.
        """
        context = super().get_context()
        context["content"] = self.content
        return context

    @classmethod
    def as_tag(cls):
        """Return a template tag function with content as first arg, plus any Meta.positional_args."""
        positional_args = cls.get_positional_args()

        def _tag(content, *args, **kwargs):
            cls.map_positional_args(positional_args, args, kwargs)
            return cls(content=content, **kwargs)

        return _tag

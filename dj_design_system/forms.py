"""Form factory for generating parameter forms in the design system gallery."""

from django import forms

from dj_design_system.components import BaseComponent, BlockComponent
from dj_design_system.data import BLOCK_CONTENT_PLACEHOLDER
from dj_design_system.parameters.base import BoolParam
from dj_design_system.parameters.model import ModelParam


def build_component_form(component_class: type[BaseComponent]) -> type[forms.Form]:
    """Build a Django Form class from a component's parameter descriptors.

    The returned class is named ``ComponentParametersForm`` and has one field
    per parameter, mapped as follows:

    - ``BoolParam`` / ``BoolCSSClassParam`` → ``BooleanField(required=False)``
    - ``StrParam`` / ``StrCSSClassParam`` with choices → ``ChoiceField``; a
      blank option is prepended when the parameter is not required.
    - ``StrParam`` / ``StrCSSClassParam`` without choices → ``CharField``
    - ``ModelParam`` subclass → ``ModelChoiceField`` with the queryset
      ordered by ``-pk`` and capped at 10 items.

    For ``BlockComponent`` subclasses, a ``content`` textarea field is
    prepended to allow editing the block's inner content.

    All fields have ``required=False`` because validation is handled at the
    component level, not the form level.
    """
    params = component_class.get_params()
    fields: dict[str, forms.Field] = {}

    # BlockComponent subclasses take content as their first argument.
    if issubclass(component_class, BlockComponent):
        fields["content"] = forms.CharField(
            label="content",
            help_text="Inner block content.",
            required=False,
            initial=BLOCK_CONTENT_PLACEHOLDER,
            widget=forms.Textarea(attrs={"rows": 1}),
        )

    fields.update({name: _build_field(name, spec) for name, spec in params.items()})
    return type("ComponentParametersForm", (forms.Form,), fields)


def _build_field(name: str, spec) -> forms.Field:
    """Return the appropriate Django form field for a single parameter spec."""
    common: dict = {
        "label": name,
        "help_text": spec.description or "",
        "required": False,
    }

    # BoolParam (and its subclass BoolCSSClassParam) → True/False dropdown.
    # Check BoolParam before StrParam because BoolCSSClassParam inherits from BoolParam.
    if isinstance(spec, BoolParam):
        return forms.TypedChoiceField(
            choices=[("", "—"), ("True", "True"), ("False", "False")],
            coerce=lambda v: v == "True",
            empty_value=None,
            **common,
        )

    # ModelParam subclasses → model select, limited to 10 most-recent rows.
    if isinstance(spec, ModelParam):
        model = spec._resolve_model()
        return forms.ModelChoiceField(
            queryset=model.objects.order_by("-pk")[:10],
            **common,
        )

    # StrParam / StrCSSClassParam with choices → select.
    if spec.choices:
        choices = [(str(c), str(c)) for c in spec.choices]
        if not spec.required:
            choices = [("", "—")] + choices
        return forms.ChoiceField(choices=choices, **common)

    # StrParam / StrCSSClassParam without choices → text input.
    return forms.CharField(**common)

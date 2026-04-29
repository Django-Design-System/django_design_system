# Components

## Component Types

### TagComponent

Subclass `TagComponent` for components that produce a single HTML fragment without wrapping nested template content. These are registered as Django `simple_tag`s.

```python
from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam

class IconComponent(TagComponent):
    """Renders an SVG icon."""
    name = StrParam("The icon name.")

    class Meta:
        positional_args = ["name"]
```

Template usage: `{% icon "check" %}`

### BlockComponent

Subclass `BlockComponent` for components that wrap nested template content. These are registered as Django `simple_block_tag`s.

The block body is automatically available as `{content}` in the template format string — you do NOT need to declare it as a parameter. `content` should NOT appear in `Meta.positional_args`.

```python
from dj_design_system.components import BlockComponent
from dj_design_system.parameters import StrParam

class CalloutComponent(BlockComponent):
    """A callout box."""
    type = StrParam("Callout type.", default="info")
```

Template usage:

```html
{% callout type="warning" %} Watch out! {% endcallout %}
```

## Parameters

Parameters are declared as class attributes using descriptor classes from `dj_design_system.parameters`.

| Type                | Description                                                               |
| ------------------- | ------------------------------------------------------------------------- |
| `StrParam`          | A string parameter                                                        |
| `BoolParam`         | A boolean parameter                                                       |
| `StrCSSClassParam`  | A string parameter whose value is added as a CSS class                    |
| `BoolCSSClassParam` | A boolean parameter that adds the parameter name as a CSS class when True |
| `ModelParam`        | A parameter that accepts a Django model instance and exposes its fields   |
| `UserParam`         | A pre-configured `ModelParam` for the project's `AUTH_USER_MODEL`         |

```python
class MyComponent(TagComponent):
    label = StrParam("Display text.")
    size = StrCSSClassParam("Size.", default="medium", choices=["small", "medium", "large"])
    highlighted = BoolCSSClassParam(required=False, default=False)
```

### Parameter Options

- `description` (first positional arg): Human-readable description
- `required` (default: `True`): Whether the parameter must be provided
- `default` (default: `None`): Default value when not provided
- `choices` (default: `None`): List of allowed values

### ModelParam

`ModelParam` accepts a Django model instance and flattens its attributes into the template context. Subclass it with a `Meta` inner class:

```python
from dj_design_system.parameters import ModelParam

class ProfileParam(ModelParam):
    class Meta:
        model = "myapp.Profile"  # or the model class directly
        fields = ["display_name", "email", "is_verified"]
        bool_css_classes = [("is_verified", "verified")]
        str_css_classes = ["role"]
```

#### Meta Options

- **`model`** (required): The Django model class, or a string in `"app_label.ModelName"` format (resolved lazily via the app registry).
- **`fields`** (required): A list of attribute names to expose, or `"__all__"` for all concrete model fields. See the [security note on `__all__`](#security-fields-all) below.
- **`bool_css_classes`** (optional): A list of attribute names (or `(attr, class_name)` tuples) that generate a CSS class when truthy.
- **`str_css_classes`** (optional): A list of attribute names (or `(attr, class_name)` tuples) whose string values generate a CSS class.
- **`abstract = True`**: Marks an intermediate base class that does not need `model`/`fields`.

#### Template Context

Model attributes are flattened into the context with the parameter name as a prefix, using underscore separation. For example, a parameter named `user` with `fields = ["first_name", "email"]` produces `{user_first_name}` and `{user_email}`:

```python
class UserCardComponent(TagComponent):
    template_format_str = (
        "<div class='user-card {classes}'>"
        "<h3>{user_first_name} {user_last_name}</h3>"
        "<p>{user_email}</p>"
        "</div>"
    )
    user = UserParam("The user to display.")
```

#### CSS Classes

CSS classes are namespaced with the parameter name to avoid collisions. Given:

```python
class Meta:
    model = "auth.User"
    fields = ["first_name", "is_active", "is_superuser", "role"]
    bool_css_classes = [("is_active", "active"), "is_superuser"]
    str_css_classes = [("first_name", "name"), "role"]
```

A user with `first_name="Andrew"`, `is_active=True`, `is_superuser=True`, `role="Employee"` would produce these classes:

```
user-active user-is_superuser user-name-Andrew user-role-Employee
```

Each entry in `bool_css_classes` and `str_css_classes` can be:

- A **string** — the attribute name is also used as the CSS class name.
- A **tuple** `(attribute, class_name)` — the attribute is read from the model, and `class_name` is used in the generated CSS class.

All CSS class config entries **must reference attributes that are listed in `Meta.fields`**. This is validated at class definition time for explicit field lists, and at runtime for `"__all__"`.

#### Security: `Meta.fields` and `__all__` {#security-fields-all}

> **Prefer explicit field lists over `"__all__"`.** Using `"__all__"` exposes every concrete field on the model — including fields that may contain sensitive data (e.g. password hashes, tokens, internal IDs). If any of these values appear in template context or CSS classes, they could be rendered into HTML visible to end users.
>
> When `"__all__"` is used:
>
> - All concrete model fields are exposed in the template context as `{param_name}_{field_name}`.
> - CSS class field validation is deferred to runtime rather than being caught at class definition time.
> - New fields added to the model in future migrations will be automatically exposed without explicit review.
>
> **Always use an explicit field list** unless you have reviewed all current and likely future fields on the model and are confident none are sensitive.

### UserParam

`UserParam` is a ready-made `ModelParam` for the project's `AUTH_USER_MODEL`. It exposes `first_name`, `last_name`, `email`, and `is_active`, with `is_active` configured as a boolean CSS class (`{param_name}-active` when truthy).

```python
from dj_design_system.parameters import UserParam

class ProfileCardComponent(TagComponent):
    template_format_str = "<div class='profile {classes}'>{user_first_name}</div>"
    user = UserParam("The user.")
```

## Meta Options

Components support an inner `Meta` class for configuration:

### `abstract = True`

Marks a component as abstract — it will not be discovered or registered. Use this for base classes that other components inherit from.

```python
class AbstractCard(TagComponent):
    class Meta:
        abstract = True
```

### `name = "custom_name"`

Override the auto-derived component name. By default, names are derived from the class name by stripping a `Component` suffix and converting to snake_case (e.g. `HeroCardComponent` → `hero_card`).

```python
class HeroCardComponent(TagComponent):
    class Meta:
        name = "hero"
```

### `positional_args = ["param1", "param2"]`

Declare parameters that can be passed as positional arguments in the template tag. Arguments are mapped to parameters in order.

```python
class LinkComponent(TagComponent):
    url = StrParam("The URL.")
    label = StrParam("Link text.")

    class Meta:
        positional_args = ["url", "label"]
```

Template usage: `{% link "/about" "About Us" %}` or `{% link url="/about" label="About Us" %}`

For `BlockComponent`, `content` is handled automatically and should NOT appear in `positional_args`.

`positional_args` are NOT inherited from parent classes. Each concrete component must declare its own if needed.

### `mutually_exclusive = [("param_a", "param_b"), ...]`

Declare pairs of parameters that cannot both be set at the same time. A `ValueError` is raised during `__init__()` if both members of any pair are provided.

```python
class IconButtonComponent(TagComponent):
    icon = StrParam("Icon name.", required=False)
    label = StrParam("Button label.", required=False)
    icon_only_label = StrParam("Accessible label when no visible text is shown.", required=False)

    class Meta:
        mutually_exclusive = [("label", "icon_only_label")]
```

All param names referenced in `mutually_exclusive` must exist on the component — this is validated at class definition time and raises `ValueError` immediately if a name is wrong.

### `requires = [("dependent", "dependency"), ...]`

Declare that setting one parameter requires another to also be set. A `ValueError` is raised during `__init__()` if `dependent` is set but `dependency` is not.

```python
class IconButtonComponent(TagComponent):
    icon = StrParam("Icon name.", required=False)
    icon_label = StrParam("Accessible label for the icon.", required=False)

    class Meta:
        requires = [("icon", "icon_label")]
```

Setting `dependency` alone (without `dependent`) is always valid — the constraint only applies in one direction.

Both `mutually_exclusive` and `requires` can be combined on the same component, and multiple pairs can be declared in each list. Meta constraints are enforced before the [`validate_params()`](#validate_params) override hook runs.

## Override Hooks

### `validate_params()`

Override to enforce additional parameter constraints beyond what `Meta.mutually_exclusive` and `Meta.requires` can express. Called during `__init__()` after all parameters are set, and after Meta constraints have already been checked.

```python
def validate_params(self):
    if self.type == "warning" and self.embedded:
        raise ValueError("Embedded callouts cannot be warnings.")
```

### `get_context()`

Override to add or modify template context variables beyond the auto-collected parameters and CSS classes.

```python
def get_context(self):
    super().get_context()
    self.context["icon"] = IconComponent(name=self.icon_name)
    return self.context
```

### `get_classes_string()`

Override to customise the CSS class string generation.

```python
def get_classes_string(self):
    return f"content-icon {super().get_classes_string()}".strip()
```

## Component Media

Components can declare the CSS and JS files they need to render correctly. This is exposed through `ComponentInfo.media` (from the registry) and `MyComponent.get_media()` (on the class itself), both of which return a `ComponentMedia` object with `css` and `js` attributes — each a list of Django static URL strings.

### Auto-discovery

By default, the registry looks for a CSS file and a JS file **in the same directory as the component's Python file**, named after the component. For example, if the component name is `icon`, it looks for `icon.css` and `icon.js` next to the Python file. Only files that actually exist on disk are included.

```
myapp/components/icon/
    component.py       # defines IconComponent (name: "icon")
    icon.css           # automatically discovered
    icon.js            # automatically discovered
```

The resulting static URL would be `myapp/components/icon/icon.css`.

### Explicit Media class

Add a `Media` inner class to declare additional CSS or JS files beyond those found by auto-discovery. This uses the same convention as Django form widgets. Provide full Django static URL paths:

```python
class IconComponent(TagComponent):
    """Renders an SVG icon."""
    name = StrParam("The icon name.")

    class Media:
        css = ["myapp/components/icon/icon-extra.css"]
        js = "myapp/components/icon/icon.js"  # single string is also accepted
```

Auto-discovery always runs regardless of whether a `Media` class is present. Explicit `Media` entries appear first in the merged result; co-located files found by auto-discovery are appended (duplicates are removed).

### Inheritance

Media definitions are merged across the MRO (method resolution order), with parent media appearing first and child additions appended. Duplicate paths are removed.

```python
class BaseCard(TagComponent):
    class Media:
        css = ["myapp/components/card/base.css"]

class FancyCard(BaseCard):
    class Media:
        css = ["myapp/components/card/fancy.css"]

# FancyCard.get_media().css ==
# ["myapp/components/card/base.css", "myapp/components/card/fancy.css"]
```

### Accessing media in code

```python
from dj_design_system import component_registry

# Via the registry
info = component_registry.get_by_name("icon", app_label="myapp")
print(info.media.css)   # ['myapp/components/icon/icon.css']
print(info.media.js)    # []

# Via the component class directly
from myapp.components.icon import IconComponent
media = IconComponent.get_media()
print(media.css)
```

## Documentation

### Markdown files

Place an `index.md` file in a component's directory to add documentation
that appears below the parameters table on the component's gallery page.
Other `.md` files appear as standalone document nodes in the sidebar.

### Live demos in documentation

Use fenced `canvas` blocks to embed live component previews in any
markdown file. The syntax mirrors the template tag usage:

````markdown
```canvas
{% icon "check" size="large" %}
```
````

Each block renders as a widget with a live preview and a
syntax-highlighted code block. See the
[gallery documentation](gallery.md#live-demos-in-markdown) for full
details.

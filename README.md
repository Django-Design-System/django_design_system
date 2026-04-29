# dj-design-system

[![Unit tests](https://github.com/Django-Design-System/django_design_system/actions/workflows/test.yml/badge.svg)](https://github.com/Django-Design-System/django_design_system/actions/workflows/test.yml)
[![Lint](https://github.com/Django-Design-System/django_design_system/actions/workflows/lint.yml/badge.svg)](https://github.com/Django-Design-System/django_design_system/actions/workflows/lint.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)
[![Django 5.2+](https://img.shields.io/badge/django-5.2%2B-green)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

DjDS is a Django-native approach to writing front end components that are exposed as templatetags. It comes with an auto-generated, customisable, live interactive gallery of your UI components that lives alongside your Django project.

Components are recognisably Django elements; they look and work like Models or Forms. The gallery auto-discovers them, renders live previews in sandboxed iframes, generates templatetag usage examples, and builds a searchable navigation tree — all from your existing code and docstrings.

## Quick start

```bash
pip install dj-design-system
```

Then follow the [quickstart guide](docs/quickstart.md) to register your first component.

## Documentation

Full documentation lives in the [`docs/`](docs/) directory and can be browsed locally with:

```bash
make docs-serve
```

| Document                                     | Contents                                  |
| -------------------------------------------- | ----------------------------------------- |
| [docs/quickstart.md](docs/quickstart.md)     | Installation and first component          |
| [docs/components.md](docs/components.md)     | Defining components and parameters        |
| [docs/registry.md](docs/registry.md)         | Auto-discovery and the component registry |
| [docs/gallery.md](docs/gallery.md)           | Configuring and customising the gallery   |
| [docs/templatetags.md](docs/templatetags.md) | Using components in templates             |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to set up a dev environment, run tests, and submit a pull request.

## Issues and feature requests

Please open an issue on [GitHub](https://github.com/Django-Design-System/django_design_system/issues). Use the bug report template for defects and the feature request template for new ideas.

## Security

To report a vulnerability privately, see [SECURITY.md](SECURITY.md).

## Licence

[MIT](LICENSE)

With thanks to the UK [Department for Business and Trade](https://github.com/uktrade), where this was originally developed.

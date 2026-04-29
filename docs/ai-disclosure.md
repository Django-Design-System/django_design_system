# AI Assistance Disclosure

This project was built with extensive use of AI coding assistants (primarily GitHub Copilot using Claude models).

## What this means in practice

**We stand behind the Python code.** The core library — components, parameters, registry,
services, views, and tests — has been reviewed, understood, and deliberately chosen by the
maintainers. AI suggestions were accepted only where they were correct and appropriate;
they were edited or rejected where they were not. The test suite exists precisely to catch
cases where they were not.

**The gallery front-end is a different story.** The HTML templates, CSS, and JavaScript
that power the interactive gallery were also produced with heavy AI assistance, and they
have not been scrutinised to the same standard. They work, but they are not a model of
best-practice front-end engineering. Specifically:

- The CSS uses a flat custom-property system rather than a structured design token approach.
- The JavaScript is functional but could benefit from a cleaner architecture.
- Accessibility has not been formally audited.
- The HTML structure has not been reviewed for semantic correctness throughout.

## What we'd welcome

Contributions that improve the gallery front-end are very welcome — whether that is
a focused accessibility fix, a CSS refactor, a JS improvement, or a full template review.
See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to get started.

We have been intentionally transparent about this rather than pretending the code is
something it is not. If you spot something that concerns you, please
[open an issue](https://github.com/Django-Design-System/django_design_system/issues).

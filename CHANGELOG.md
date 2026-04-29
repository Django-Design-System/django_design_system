# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1] - unreleased

### Added

- `TagComponent` and `BlockComponent` base classes for defining UI components
- Parameter system: `StrParam`, `BoolParam`, `StrCSSClassParam`, `BoolCSSClassParam`, `ModelParam`, `UserParam`, `FieldParam`
- Auto-discovery of components via Django's app registry (`AppConfig.ready()`)
- Component registry with lookup, listing, and navigation tree APIs
- Interactive gallery with live component previews in sandboxed iframes
- Searchable navigation tree with folder, component, and documentation node types
- Auto-generated templatetag usage examples from parameter definitions
- `ComponentsStaticFinder` to serve per-component CSS/JS via Django staticfiles
- Markdown documentation pages auto-discovered alongside components
- Configurable canvas backgrounds, toolbar, and gallery settings via `dj_design_system` Django settings dict

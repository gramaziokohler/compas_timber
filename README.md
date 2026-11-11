<h1>
  <img src="docs/_logo/PNG_tranparent-background.png" alt="COMPAS Timber logo" width="70" height="70" align="absmiddle"> COMPAS Timber
</h1>


[![Github Actions Build Status](https://github.com/gramaziokohler/compas_timber/workflows/build/badge.svg)](https://github.com/gramaziokohler/compas_timber/actions)
[![codecov](https://codecov.io/gh/gramaziokohler/compas_timber/graph/badge.svg?token=EFI7G1T18Z)](https://codecov.io/gh/gramaziokohler/compas_timber)
[![License](https://img.shields.io/github/license/gramaziokohler/compas_timber.svg)](https://pypi.python.org/pypi/compas_timber)
[![pip downloads](https://img.shields.io/pypi/dm/compas_timber)](https://pypi.python.org/project/compas_timber)
[![PyPI Package latest release](https://img.shields.io/pypi/v/compas_timber.svg)](https://pypi.python.org/pypi/compas_timber)
[![Supported implementations](https://img.shields.io/pypi/implementation/compas_timber.svg)](https://pypi.python.org/pypi/compas_timber)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.7934266-blue)](https://doi.org/10.5281/zenodo.7934266)
[![Twitter Follow](https://img.shields.io/twitter/follow/compas_dev?style=social)](https://twitter.com/compas_dev)
[![Made with COMPAS](https://compas.dev/badge.svg)](https://compas.dev/#/)
![COMPAS Timber](https://raw.githubusercontent.com/gramaziokohler/compas_timber/main/docs/_images/compas_timber.jpg)

`compas_timber` is a user-friendly open-source software toolkit that streamlines the design-to-fabrication workflow of timber frame structures. A project is designed and refined in a single digital model that also produces the manufacturing data, so it can go from first concept to fabrication without re-modeling or back-and-forth rework along the way. By lowering the threshold for creating versatile and resource-aware timber designs, we aim to increase the use of timber in architecture.

## Installation

We recommend managing environments and dependencies with [uv](https://docs.astral.sh/uv/), but a plain `pip install compas_timber` works just as well.

Add `compas_timber` to your project:

```bash
uv add compas_timber
```

To visualize models outside of Rhino, install with the `viz` extra, which adds [compas_viewer](https://github.com/compas-dev/compas_viewer) and `compas_brep[occ]`:

```bash
uv add "compas_timber[viz]"
```

For a development setup, clone the repository and sync the environment:

```bash
git clone https://github.com/gramaziokohler/compas_timber.git
cd compas_timber
uv sync --extra dev
uv run pytest
```

## First Steps

* [Documentation](https://gramaziokohler.github.io/compas_timber/)
* [COMPAS TIMBER Grasshopper Plugin (timber_design)](https://github.com/gramaziokohler/timber_design)
* [COMPAS TIMBER Grasshopper Tutorial](https://gramaziokohler.github.io/timber_design/)
* [COMPAS TIMBER API Reference](https://gramaziokohler.github.io/compas_timber/latest/api/compas_timber.model/)

## Questions and feedback

We encourage the use of the [COMPAS framework forum](https://forum.compas-framework.org/)
for questions and discussions.

## Issue tracker

If you found an issue or have a suggestion for a dandy new feature, please file a new issue in our [issue tracker](https://github.com/gramaziokohler/compas_timber/issues).

## Contributing

We love contributions!

Check the [Contributor's Guide](CONTRIBUTING.md)
for more details.

## Credits

`compas_timber` is currently developed by Gramazio Kohler Research. See [`CITATION.cff`](CITATION.cff) for a complete list of authors.

# Contributing

Contributions are welcome and very much appreciated!

## Code contributions

We accept code contributions through pull requests.
In short, this is how that works.

1. Fork [the repository](https://github.com/gramaziokohler/compas_timber) and clone the fork.
   (Members of the `gramaziokohler` organization have write access and can skip the fork: clone the repository directly and work on a branch.)
2. Create a virtual environment and install development dependencies. Using [uv](https://docs.astral.sh/uv/) (recommended — uses the committed `uv.lock`):

   ```bash
   uv sync --extra dev
   ```

   Or with pip in a virtual environment of your choice (e.g. `virtualenv`, `conda`, etc.):

   ```bash
   pip install -e ".[dev]"
   ```

3. Make sure all tests pass:

   ```bash
   invoke test
   ```

4. Start making your changes to the **main** branch (or branch off of it).
5. Make sure all tests still pass:

   ```bash
   invoke test
   ```

6. Add yourself to the authors list in `CITATION.cff`. That is the only place authors are listed by hand: `pyproject.toml` and the docs are generated from it on release and on docs build.

   ```mermaid
   %%{init: {"flowchart": {"wrappingWidth": 260}}}%%
   flowchart TB
       CFF["<b>CITATION.cff</b><br/>hand-edited · the only author list"]:::focal

       CFF --> GH["<b>GitHub</b><br/><i>Cite this repository</i>"]:::out
       CFF --> ZEN["<b>Zenodo</b><br/>read when a release is archived"]:::out
       CFF --> PYPI["<b>PyPI</b><br/><i>release workflow</i>: <span style="font-family:monospace">invoke pre‑build</span> regenerates pyproject.toml authors"]:::out
       CFF --> CITE["<b>Docs citing page</b><br/><i>docs workflow</i>: mkdocs hook fills the BibTeX author block at build time"]:::out

       classDef focal fill:#fde7db,stroke:#eb6c36,stroke-width:1.5px,color:#2d3142
       classDef out fill:#e9ebf0,stroke:#7a8399,stroke-width:1px,color:#2d3142
   ```

7. Commit your changes and push your branch to GitHub.
8. Create a [pull request](https://help.github.com/articles/about-pull-requests/) through the GitHub website.

During development, use [pyinvoke](http://docs.pyinvoke.org/) tasks on the
command line to ease recurring operations:

* `invoke clean`: Clean all generated artifacts.
* `invoke check`: Run various code and documentation style checks.
* `invoke docs`: Generate documentation.
* `invoke test`: Run all tests and checks in one swift command.
* `invoke`: Show available tasks.

## Bug reports

When [reporting a bug](https://github.com/gramaziokohler/compas_timber/issues) please include:

* Operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

## Feature requests

When [proposing a new feature](https://github.com/gramaziokohler/compas_timber/issues) please include:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.

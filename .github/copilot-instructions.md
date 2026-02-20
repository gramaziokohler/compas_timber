# COMPAS TIMBER

COMPAS Timber is an open-source software toolkit to streamline the design of timber frame structures. Despite its advances in digitalization compared to other building techniques, timber construction is often perceived as a challenging field, involving intricate processes in design, planning, coordination, and fabrication. We aim to increase the use of timber in architecture by lowering the threshold of creating versatile and resource-aware designs.

## Working Effectively
- Bootstrap and install development dependencies:
  - `pip install -e .[dev]` -- installs all dev tools and the package in editable mode. Takes ~60 seconds with good network.
  - **NOTE**: May fail in environments with restricted network access. If pip times out, dependencies may need manual installation.
- **NEVER CANCEL**: Set timeout to 300+ seconds for dependency installation in case of slow network.
- `invoke clean` -- clean all generated artifacts. Takes ~1 second.
- `invoke lint` -- run ruff and black linters. Takes ~1 second.
- `invoke format` -- reformat code with black. Takes ~1 second.  
- `invoke check` -- comprehensive style and metadata checks. Takes ~2 seconds.
- `mkdocs build -c` -- build HTML documentation with mkdocs-material. May take several minutes.
- `invoke test` -- run unit tests. Takes ~6 seconds.

## Validation
- Always run `invoke clean && invoke lint && invoke format && invoke check` before committing changes.
- **VALIDATION SCENARIOS**: Test basic functionality after changes:
  - `python -m compas_timber.__version__` -- should print "COMPAS TIMBER v1.0.0 is installed!"
- The CI will run tests on Windows, macOS, Linux with Python 3.9, 3.10, 3.11, 3.12 AND IronPython 2.7.

## Installation & Dependencies
- **Python Requirements**: Python 3.9+ (supports CPython and IronPython)
- **Core Dependencies**: compas>=2.0, compas_model==0.4.4
- **Development Tools**: invoke, pytest, black, mkdocs-material
- **Development Installation**: `pip install -e .[dev]` (installs package in editable mode)

## Code Style & Documentation
- **Docstring Style**: Use numpy-style docstrings for all functions, classes, and methods. Properties docstrings are part of the class's docstring.
- **Code Formatting**: Use `invoke format` to automatically format code with `black`
- **Linting**: Use `invoke lint` to check code style with `ruff` and `black`
- **Type Hints**: Include type hints where appropriate for better code clarity, as long as it's compatible with IronPython (comment hints)

## Build System
- Uses **setuptools** with `pyproject.toml`
- **invoke** task runner for automation (replaces Make/scripts)
- **pytest** for testing with doctest integration
- **mkdocs-material** for documentation
- No compiled components - pure Python package

## CI/CD Integration
- GitHub Actions workflows in `.github/workflows/`
- Tests run on multiple OS/Python combinations
- **Always run** `invoke lint` before pushing - CI enforces code style
- Uses `compas-dev/compas-actions.build@v4` for standard COMPAS project workflows

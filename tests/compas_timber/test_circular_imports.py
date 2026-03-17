"""Test that every public module can be imported in isolation without circular import errors.

Circular imports in Python are order-dependent: importing module A first may
succeed while importing module B first may fail.  Normal test runs hide this
because pytest's collection imports modules in a fixed order that may
accidentally resolve the cycle.

This test spawns a **fresh Python subprocess** for each module so that no prior
imports can mask a cycle.
"""

import subprocess
import sys

import pytest

# All public compas_timber modules (packages and standalone modules).
# Add new modules here as they are created.
MODULES = [
    "compas_timber",
    "compas_timber.analyzers",
    "compas_timber.base",
    "compas_timber.connections",
    "compas_timber.elements",
    "compas_timber.errors",
    "compas_timber.fabrication",
    "compas_timber.geometry",
    "compas_timber.model",
    "compas_timber.panel_features",
    "compas_timber.planning",
    "compas_timber.structural",
]


@pytest.mark.parametrize("module", MODULES)
def test_import_no_circular_dependency(module):
    """Importing *module* in a clean interpreter must not raise ImportError."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Importing {module} failed:\n{result.stderr}"

import os
from .__version__ import __version__


HERE = os.path.dirname(__file__)
DATA = os.path.abspath(os.path.join(HERE, "..", "..", "data"))


__all_plugins__ = [
    "compas_timber.ghpython.install",
    "compas_timber.rhino",
    "compas_timber.rhino.install",
    "compas_timber.utils.r_tree",
]


__all__ = ["__version__", "DATA"]

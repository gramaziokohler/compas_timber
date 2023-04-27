"""
********************************************************************************
utils
********************************************************************************

.. currentmodule:: compas_timber.utils

.. rst-class:: lead

Functions
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    intersection_line_line_3D
    intersection_line_plane

"""

from .compas_extra import intersection_line_line_3D
from .compas_extra import intersection_line_plane

from .helpers import close
from .helpers import are_objects_identical

__all__ = [
    "intersection_line_line_3D",
    "intersection_line_plane",
    "close",
    "are_objects_identical",
]

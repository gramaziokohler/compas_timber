"""
********************************************************************************
parts
********************************************************************************

.. currentmodule:: compas_timber.parts

.. rst-class:: lead

The modules in Elements describe simple, re-usable elements such as a beam, a rod or a plate.

Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    Beam
"""
from .beam import Beam
from .features import CutFeature
from .features import DrillFeature
from .features import MillVolume

__all__ = [
    "Beam",
    "CutFeature",
    "DrillFeature",
    "MillVolume",
]

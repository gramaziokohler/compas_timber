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
from .features import BeamTrimmingFeature
from .features import BeamExtensionFeature
from .features import BeamBooleanSubtraction

__all__ = [
    "Beam",
    "BeamTrimmingFeature",
    "BeamExtensionFeature",
    "BeamBooleanSubtraction",
]

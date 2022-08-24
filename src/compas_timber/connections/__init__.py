"""
********************************************************************************
connections
********************************************************************************

.. currentmodule:: compas_timber.connections

.. rst-class:: lead

Connections are a collection of tools to generate joint geometries.

Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    TButtJoint
"""
from .joint import Joint
from .t_butt import TButtJoint

__all__ = [
    "Joint",
    "TButtJoint",
]

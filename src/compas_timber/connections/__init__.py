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

    Joint
    TButtJoint
    LButtJoint
    LMiterJoint
    XHalfLapJoint
    JointTopology
    ConnectionSolver

Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    find_neighboring_beams

Exceptions
==========
.. autosummary::
    :toctree: generated/
    :nosignatures:

    BeamJoinningError

"""
from .joint import Joint
from .joint import JointOptions
from .joint import beam_side_incidence
from .joint import BeamJoinningError
from .t_butt import TButtJoint
from .l_butt import LButtJoint
from .l_miter import LMiterJoint
from .x_halflap import XHalfLapJoint
from .t_halflap import THalfLapJoint
from .l_halflap import LHalfLapJoint
from .french_ridge_lap import FrenchRidgeLapJoint
from .solver import JointTopology
from .solver import ConnectionSolver
from .solver import find_neighboring_beams


__all__ = [
    "Joint",
    "JointOptions",
    "beam_side_incidence",
    "BeamJoinningError",
    "TButtJoint",
    "LButtJoint",
    "LMiterJoint",
    "XHalfLapJoint",
    "THalfLapJoint",
    "LHalfLapJoint",
    "FrenchRidgeLapJoint",
    "JointTopology",
    "ConnectionSolver",
    "find_neighboring_beams",
]

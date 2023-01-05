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
from .joint import beam_side_incidence
from .joint import BeamJoinningError
from .t_butt import TButtJoint
from .t_lap import TLapJoint
from .l_butt import LButtJoint
from .l_miter import LMiterJoint
from .x_lap import XLapJoint
from .solver import JointTopology
from .solver import ConnectionSolver


__all__ = [
    "Joint",
    "BeamJoinningError",
    "TButtJoint",
    "TLapJoint",
    "LButtJoint",
    "LMiterJoint",
    "XLapJoint",
    "beam_side_incidence",
    "JointTopology",
    "ConnectionSolver",
]

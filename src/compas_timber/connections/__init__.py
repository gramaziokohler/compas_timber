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

Functions
=========

    beam_side_incidence

"""
from .joint import Joint
from .joint import beam_side_incidence
from .joint import BeamJoinningError
from .t_butt import TButtJoint
from .l_butt import LButtJoint
from .l_miter import LMiterJoint
from .solver import JointTopology
from .solver import ConnectionSolver


__all__ = [
    "Joint",
    "beam_side_incidence",
    "BeamJoinningError",
    "TButtJoint",
    "LButtJoint",
    "LMiterJoint",
    "JointTopology",
    "ConnectionSolver",
]

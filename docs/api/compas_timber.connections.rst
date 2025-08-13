********************************************************************************
compas_timber.connections
********************************************************************************

.. currentmodule:: compas_timber.connections

Joints
======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    BallNodeJoint
    Joint
    LapJoint
    LButtJoint
    LFrenchRidgeLapJoint
    LLapJoint
    LMiterJoint
    JointCandidate
    TBirdsmouthJoint
    TButtJoint
    TDovetailJoint
    TLapJoint
    TStepJoint
    TenonMortiseJoint
    XLapJoint
    XNotchJoint
    YButtJoint

Solvers
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    ConnectionSolver
    JointTopology
    Cluster
    BeamGroupAnalyzer
    NBeamKDTreeAnalyzer
    TripletAnalyzer
    QuadAnalyzer
    CompositeAnalyzer

Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    find_neighboring_elements

Exceptions
==========

The following exceptions may be raised by this module. See the :mod:`compas_timber.errors` module for details.

- :class:`compas_timber.errors.BeamJoiningError`
- :class:`compas_timber.errors.FeatureApplicationError`
- :class:`compas_timber.errors.FastenerApplicationError`

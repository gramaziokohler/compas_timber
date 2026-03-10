********************************************************************************
compas_timber.connections
********************************************************************************

.. currentmodule:: compas_timber.connections

Joints
======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    Joint
    PlateJoint
    LapJoint
    ButtJoint
    TButtJoint
    LButtJoint
    TStepJoint
    LFrenchRidgeLapJoint
    LLapJoint
    LMiterJoint
    JointCandidate
    PlateJointCandidate
    TBirdsmouthJoint
    LMiterJoint
    XLapJoint
    XNotchJoint
    TLapJoint
    LLapJoint
    JointCandidate
    LFrenchRidgeLapJoint
    JointTopology
    ConnectionSolver
    PlateConnectionSolver
    TDovetailJoint
    BallNodeJoint
    LTenonMortiseJoint
    TTenonMortiseJoint
    YButtJoint
    TOliGinaJoint
    PlateJoint
    PlateButtJoint
    PlateLButtJoint
    PlateTButtJoint
    PlateMiterJoint


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
    MaxNCompositeAnalyzer

Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    find_neighboring_elements
    beam_ref_side_incidence
    beam_ref_side_incidence_with_vector
    point_centerline_towards_joint

Exceptions
==========

The following exceptions may be raised by this module. See the :mod:`compas_timber.errors` module for details.

- :class:`compas_timber.errors.BeamJoiningError`
- :class:`compas_timber.errors.FeatureApplicationError`
- :class:`compas_timber.errors.FastenerApplicationError`

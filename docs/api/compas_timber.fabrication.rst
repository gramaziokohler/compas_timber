********************************************************************************
compas_timber.fabrication
********************************************************************************

.. currentmodule:: compas_timber.fabrication

Core
====

.. autosummary::
    :toctree: generated/
    :nosignatures:

    BTLxWriter
    BTLxPart
    BTLxProcessing
    BTLxFromGeometryDefinition

Processings
===========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    DoubleCut
    DovetailTenon
    DovetailMortise
    Drilling
    FrenchRidgeLap
    JackRafterCut
    Lap
    LongitudinalCut
    Pocket
    Slot
    StepJoint
    StepJointNotch
    Tenon
    Mortise
    FreeContour
    Text

Processings Parameters
======================

.. autosummary::
    :toctree: generated/
    :nosignatures:

    AlignmentType
    EdgePositionType
    LimitationTopType
    MachiningLimits
    OrientationType
    StepShapeType
    TenonShapeType
    Contour
    DualContour

Processings Proxies
===================

Proxies can be used interchangably with their corresponding processings in-order to speed up visualization.
Upon creating a BTLx file, these are converted to their respective processings.

.. autosummary::
    :toctree: generated/
    :nosignatures:

    JackRafterCutProxy
    PocketProxy
    LapProxy


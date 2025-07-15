**********************************************
BTLx Contribution Guide
**********************************************

BTLx processings are machining operations that can be applied to timber elements. This guide provides step-by-step instructions for creating new BTLx processings and integrating them with the COMPAS Timber framework.

.. note::
    For implementing new joint types from already existing BTLx Processings, see the :doc:`Joint Contribution Guide`.

Adding a new BTLx Processing
============================

1. Identify the BTLx Processing and Parameters
----------------------------------------------

First, identify the specific BTLx processing you want to implement from the official BTLx specification: https://design2machine.com/btlx/btlx_2_1_0.pdf

Study the processing definition to understand:

- All required parameters and their data types
- Parameter constraints and valid ranges
- The geometric meaning of each parameter

2. Create the Processing Class
------------------------------

Create a new module in ``src/compas_timber/fabrication/`` that inherits from ``BTLxProcessing``.
It is important to implement the following methods and attributes:

- ``PROCESSING_NAME``: class attribute matching BTLx specification
- ``__init__()``: method with parameter validation
- ``params``: property returning a parameters instance for serialization
- ``apply()``: method that uses your geometry generation method to modify the element geometry and return the result (use appropriate error handling with ``FeatureApplicationError``)
- ``scale()``: method for parameter scaling when units are not set in mm

.. note::

    See also:

    - :meth:`compas_timber.fabrication.JackRafterCut`
    - :meth:`compas_timber.fabrication.Lap`


3. Add Alternative Constructors in Processing Class
---------------------------------------------------

Implement class methods to create processings from geometric inputs.

This is the **geometry → parameters** conversion used in joint implementations.

**What to implement:**

- At least one alternative constructor that takes geometric objects and the target element
- Extract BTLx parameters from the geometry-element relationship
- Return a new processing instance with calculated parameters

**Naming convention:** Use descriptive method names that specify the geometric input and target element.

.. note::

    See also:

    - :meth:`compas_timber.fabrication.JackRafterCut.from_plane_and_beam`
    - :meth:`compas_timber.fabrication.Lap.from_volume_and_beam`

4. Add Geometry Generation Method in Processing Class
-----------------------------------------------------

Implement a method to convert BTLx parameters back to geometry.

This is the **parameters → geometry** conversion used in the ``apply()`` method and must be the inverse of the alternative constructor.

**What to implement:**

- A method that returns the geometric object needed for the processing operation (cutting plane, mill volume, etc.)
- Ensure it's the inverse of your alternative constructor
- This geometry will be used by the ``apply()`` method to modify the element geometry and return the result (use appropriate error handling with ``FeatureApplicationError``)

**Naming convention:** Use descriptive method names that specify the expected geometric output.

.. note::

    See also:

    - :meth:`compas_timber.fabrication.JackRafterCut.plane_from_params_and_beam`
    - :meth:`compas_timber.fabrication.Lap.volume_from_params_and_beam`

5. Create the Parameters Class
------------------------------

Create a parameters class for BTLx serialization. This class converts your processing instance into dictionary with BTLx parameter names and values as keys and values. This is then used by the ``BTLxWriter`` to serialize the processing to XML.

6. Update Module Imports
------------------------

Add your new processing to ``src/compas_timber/fabrication/__init__.py`` so it can be imported by other modules.

7. Add Tests
------------

Add unit tests in ``tests/compas_timber/`` to verify your processing works correctly. Ensure you cover:
- Parameter validation
- Geometry conversion methods
- Geometry modification in the ``apply()`` method


Key Considerations
==================

**Reference Sides**: BTLx uses reference sides (RS1-RS6) to define coordinate systems. Use the ``ref_side_index`` parameter to specify which face of the element is the reference.

.. note::
    The BTLx specification uses 1-based indexing for reference sides (RS1-RS6), but ``compas_timber`` uses 0-based indexing internally (0-5). The ``BTLxWriter`` automatically converts from 0-based to 1-based indexing when serializing to BTLx XML format.

**Local Coordinate System**: All BTLx parameters must be defined in the local coordinate system of the element's `ReferenceSide`. When implementing alternative constructors, ensure geometric calculations are converted to the element's local space.

**Bidirectional Geometry-Parameter Conversion**: Implement both directions of conversion:

- Alternative constructors convert geometry → BTLx parameters
- Geometry generation methods convert BTLx parameters → geometry

These methods are inverse operations and should be consistent with each other.


Example: Looking at Existing Processings
========================================

Study existing processings like ``JackRafterCut``, ``Lap``, ``StepJoint``, ``Tenon`` in the fabrication module to understand the patterns and best practices used in the codebase.

**********************************************
BTLx Contribution Guide
**********************************************

BTLx processings are machining operations that can be applied to timber elements. This guide provides step-by-step instructions for creating new BTLx processings and integrating them with the COMPAS Timber framework.

.. note::
    For implementing new joint types from already existing BTLx Processings, see the :doc:`Joint Contribution Guide <joints_contribution_guide>`.

Adding a new BTLx Processing
============================

1. Identify the BTLx Processing and Parameters
----------------------------------------------

First, identify the specific BTLx processing you want to implement from the official BTLx specification: https://design2machine.com/btlx/btlx_2_3_0.pdf

Study the processing definition to understand:

- All required parameters and their data types
- Parameter constraints and valid ranges
- The geometric meaning of each parameter

2. Create the Processing Class
------------------------------

Create a new module in ``src/compas_timber/fabrication/`` that inherits from ``BTLxProcessing``.
The following methods and attributes are the absolute minimum required to implement a processing:

- ``PROCESSING_NAME`` : Class attribute matching BTLx specification
- ``ATTRIBUTE_MAP`` : Class attribute dictionary mapping BTLx XML parameter names to Python attribute names
- ``__init__()`` : Method with meaningful defaults set by the BTLx specification
- ``__data__`` : Property returning a dictionary of processing data for serialization
- ``scale()`` : Method for scaling parameters when units are not set in mm


Example:
~~~~~~~~

.. code-block:: python

    class NewProcessing(BTLxProcessing):
        PROCESSING_NAME = "HypotheticalProcessing"  # need to match the name in the BTLx specification

        # Map BTLx XML parameter names to Python attribute names
        ATTRIBUTE_MAP = {
            "ArgA": "arg_a",  # BTLx name : Python attribute name
            "ArgB": "arg_b",
        }

        @property
        def __data__(self):
            data = super(NewProcessing, self).__data__
            data["arg_a"] = self.arg_a
            data["arg_b"] = self.arg_b
            return data

        def __init__(self, arg_a, arg_b, **kwargs):
            super(NewProcessing, self).__init__(**kwargs)
            self.arg_a = arg_a
            self.arg_b = arg_b

        def scale(self, factor):
            self.arg_a *= factor
            self.arg_b *= factor

.. note::
    The ``params`` property is automatically inherited from ``BTLxProcessing`` and uses the ``ATTRIBUTE_MAP`` to serialize the processing parameters. The ``BTLxProcessingParams`` class handles the conversion of Python attribute values to BTLx-compliant string formats.

.. seealso::
    :class:`JackRafterCut <compas_timber.fabrication.JackRafterCut>`
    :class:`Lap <compas_timber.fabrication.Lap>`
    :class:`Drilling <compas_timber.fabrication.Drilling>`
    :class:`DoubleCut <compas_timber.fabrication.DoubleCut>`
    :class:`FrenchRidgeLap <compas_timber.fabrication.FrenchRidgeLap>`

3. Add Alternative Constructors in Processing Class
---------------------------------------------------

Implement class methods to create processings from geometric inputs.

This is the **geometry → parameters** conversion used in joint implementations.

**What to implement:**

- At least one alternative constructor that takes geometric objects and the target element
- Extract BTLx parameters from the geometry-element relationship
- Return a new processing instance with calculated parameters
- A generic ``from_shapes_and_element()`` method that calls your specific alternative constructor

Example:
~~~~~~~~
.. code-block:: python

    class NewProcessing(BTLxProcessing):
        @classmethod
        def from_anygeometry_and_element(cls, geometry, element, additional_arg_1=None, additional_arg_2=None):
            # Extract parameters from the geometry and element
            arg_a = calculate_arg_a(geometry, element)
            arg_b = calculate_arg_b(geometry, element)
            return cls(arg_a=arg_a, arg_b=arg_b, arg_c=additional_arg_1, arg_d=additional_arg_2)

        @classmethod
        def from_shapes_and_element(cls, geometry, element, **kwargs):
            # Call the specific constructor implemented above
            return cls.from_anygeometry_and_element(geometry, element, **kwargs)


**Naming convention:** Use descriptive method names that specify the geometric input and target element.

.. seealso::
    :meth:`JackRafterCut.from_plane_and_beam() <compas_timber.fabrication.JackRafterCut.from_plane_and_beam>`
    :meth:`Lap.from_volume_and_beam() <compas_timber.fabrication.Lap.from_volume_and_beam>`
    :meth:`Drilling.from_line_and_element() <compas_timber.fabrication.Drilling.from_line_and_element>`
    :meth:`DoubleCut.from_planes_and_beam() <compas_timber.fabrication.DoubleCut.from_planes_and_beam>`
    :meth:`FrenchRidgeLap.from_beam_beam_and_plane() <compas_timber.fabrication.FrenchRidgeLap.from_beam_beam_and_plane>`

4. Add Geometry Generation Method in Processing Class
-----------------------------------------------------

Implement a method to convert BTLx parameters back to geometry.

This is the **parameters → geometry** conversion used in the ``apply()`` method and could be the inverse of the alternative constructor.

**What to implement:**

- A method that returns the geometric object needed for the processing operation (cutting plane, mill volume, etc.)
- This geometry will be used by the ``apply()`` method to modify the element's geometry and return the result
- Use appropriate error handling with ``FeatureApplicationError`` to manage exceptions during geometry generation or application

Example:
~~~~~~~~
.. code-block:: python

    class NewProcessing(BTLxProcessing):
        def geometry_from_params_and_element(self, element):
            # Convert parameters to geometry
            # ... implementation of the parameter-to-geometry conversion ...
            return feature_geometry_generated_from_params

        def apply(self, element_geometry, element):
            # Modify the element's geometry using the generated shape
            try:
                feature_geometry = self.geometry_from_params_and_element(element)
            except Exception as e:
                raise FeatureApplicationError(feature_geometry=feature_geometry, message=f"Failed to generate geometry from parameters: {e}")

            try:
                # ... apply the shape to the element geometry
            except Exception as e:
                raise FeatureApplicationError(feature_geometry=feature_geometry, element_geometry=element_geometry, message=f"Failed to apply geometry to element: {e}")
            return modified_element_geometry

.. Note::
    While this method is typically the inverse of the alternative constructor, some processings may require generating different geometry for visualization or application purposes.

.. seealso::
    :meth:`JackRafterCut.plane_from_params_and_beam <compas_timber.fabrication.JackRafterCut.plane_from_params_and_beam>`
    :meth:`Lap.volume_from_params_and_beam <compas_timber.fabrication.Lap.volume_from_params_and_beam>`
    :meth:`Drilling.cylinder_from_params_and_element <compas_timber.fabrication.Drilling.cylinder_from_params_and_element>`
    :meth:`DoubleCut.planes_from_params_and_beam <compas_timber.fabrication.DoubleCut.planes_from_params_and_beam>`
    :meth:`FrenchRidgeLap.lap_volume_from_params_and_beam <compas_timber.fabrication.FrenchRidgeLap.lap_volume_from_params_and_beam>`

5. Update Module Imports
------------------------

Add your new processing to ``src/compas_timber/fabrication/__init__.py`` so it can be imported by other modules.

6. Add Tests
------------

Add unit tests in ``tests/compas_timber/`` to verify your processing works correctly. Ensure you cover:
- Parameter validation
- Geometry conversion methods
- Geometry modification in the ``apply()`` method


Key Considerations
==================

**Reference Sides:**
BTLx uses reference sides (RS1-RS6) to define coordinate systems. Use the ``ref_side_index`` parameter to specify which face of the element is the reference.

.. important::
    The BTLx specification uses 1-based indexing for reference sides (RS1-RS6), but ``compas_timber`` uses 0-based indexing internally (0-5). The ``BTLxWriter`` automatically converts from 0-based to 1-based indexing when serializing to BTLx XML format.

**Local Coordinate System:**
All BTLx parameters must be defined in the local coordinate system of the element's `ReferenceSide`. When implementing alternative constructors, ensure geometric calculations are converted to the element's local space.

**Bidirectional Geometry-Parameter Conversion:**
Implement both directions of conversion:

- Alternative constructors convert geometry → BTLx parameters
- Geometry generation methods convert BTLx parameters → geometry

These methods are inverse operations and should be consistent with each other.

**Documentation:**
Ensure your processing class and parameters class are well-documented, including method docstrings and parameter descriptions.

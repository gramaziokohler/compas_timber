*******************************************************************************
Joints Contribution Guide
*******************************************************************************

Joints represent the interaction between two or more timber elements to form structural connections. They coordinate the application of BTLx processings (features) across participating elements to achieve the desired joint geometry.

.. note::
    For implementing new BTLx Processings, see the :doc:`BTLx Contribution Guide <BTLx_contribution_guide>`.

Creating a New Joint
=====================

1. Define Joint Requirements
--------------------------------

Before implementation, establish:

- The specific timber joint type you're creating
- Required BTLx processings for the joint geometry
- Target elements for each processing operation

2. Analyze Element Relationships
--------------------------------

Study how the involved elements interact geometrically:

**Identify Joint Topology**: Determine the connection topology using standard notation:

- ``X-TOPO``: Elements both interacting somewhere along their lengths
- ``L-TOPO``: Elements meeting at their ends at an angle
- ``T-TOPO``: One element's end intersecting another element along its length
- ``I-TOPO``: Elements joined end-to-end in a straight line

Based on the identified topology and joint type, name the joint class accordingly (e.g., ``TButtJoint`` for a **T-TOPO** butt joint).

**Define Element Roles**: Assign specific roles to each participating element, if relevant:

.. note::

    For example, in a ``TButtJoint`` (ie. **T-TOPO**):

    - ``main_beam``: The element whose end intersects the ``cross_beam``; typically receives the cutting operation.
    - ``cross_beam``: The element intersected along its length by another beam; usually remains unmodified unless specified otherwise.


3. Extract Geometric Information
--------------------------------

Identify the spatial relationships and dimensional data needed for BTLx processing alternative constructors. These may include:

- **Reference side selection**: Determine the ``ref_side_index`` to specify which face of the beam the processing operates on (defines the beam's local coordinate system)
- **Derived geometries**: Extract geometric entities from element relationships, such as cutting planes, intersection volumes, and other relevant features.
- **Element dimensions**: Retrieve beam properties such as width, height, and length for processing parameter calculations

.. note::
    The geometric analysis described here is essential for determining the correct parameters to use with BTLx processing alternative constructors, such as ``from_plane_and_beam()`` and ``from_volume_and_beam()``.

    Consult the necessary arguments required by each BTLx processing method to ensure proper usage and integration.

4. Implement Core Methods
-------------------------------

- ``add_features()``: Create BTLx processing instances via their alternative constructors and assign them to target elements.

- ``add_extensions()``: Modify element geometry (such as extending beam lengths) to accommodate the joint requirements and ensure geometric feasibility.

- ``check_elements_compatibility()``: Validate that the elements meet necessary joint requirements if applicable, such as dimensions or coplanarity.

.. note::
    In the ``add_features()`` method, register each BTLx processing (feature) both to the corresponding element using ``element.add_features()`` and to the joint itself using ``self.features.append(feature)``.
    This ensures features are properly associated for both element modification and joint serialization.

5. Update Module Imports
------------------------

Add your new joint class to ``src/compas_timber/connections/__init__.py`` so it can be imported by other modules.

6. Add Tests
------------

Add unit tests in ``tests/compas_timber/`` to verify your joint works correctly. Ensure you cover:

- BTLx processing creation and assignment in the ``add_features()`` method
- Geometry modification in the ``add_extensions()`` method
- Compatibility checks in the ``check_elements_compatibility()`` method


Example: Looking at existing Joints
====================================

Study existing joints like :class:`TButtJoint <compas_timber.connections.TButtJoint>`, :class:`LMiterJoint <compas_timber.connections.LMiterJoint>`, :class:`XLapJoint <compas_timber.connections.XLapJoint>` in the connections module to understand the patterns and best practices used in the codebase.

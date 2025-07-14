*******************************************************************************
Joints Contribution Guide
*******************************************************************************

Joints represent the interaction between two or more timber elements to form structural connections. They coordinate the application of BTLx processings (features) across participating elements to achieve the desired joint geometry.

Creating a New Joint
=====================

1. Define Joint Requirements
--------------------------------

   Before implementation, establish:

   - The specific timber joint type you're creating
   - Required BTLx processings for the joint geometry
   - Target elements for each processing operation

2. Analyze Element Relationships
-------------------------------

   Study how the involved elements interact geometrically:

   **Identify Joint Topology**: Determine the connection topology using standard notation:

   - **X-joints**: Elements both interacting somwhere along their lengths
   - **L-joints**: Elements meeting at their ends at an angle
   - **T-joints**: One elements end intersecting another element along its length
   - **I-joints**: Elements joined end-to-end in a straight line

   **Define Element Roles**: Assign specific roles to each participating element:

   - **Cross beam**: The primary or continuous element in the joint
   - **Main beam**: The secondary element that connects to the cross beam

   **Extract Geometric Information**: Identify the spatial relationships and dimensional data needed for BTLx processing alternative constructors:

   - **Intersection geometry**: Cutting planes, intersection lines, subtracting volumes

   This geometric analysis directly informs the parameters passed to BTLx processing alternative constructors (e.g., ``from_plane_and_beam()``, ``from_volume_and_beam()``).

3. Implement Core Methods
-------------------------------

   - **add_features()**: Create BTLx processing instances via their alternative constructors and assign them to target elements.

     .. note::
         In this method, features (i.e. BTLx processings) should be registered to the joint using ``self.add_features()`` and also added to their targeted elements using ``element.add_features()``.

   - **add_extensions()**: Modify element geometry (such as extending beam lengths) to accommodate the joint requirements and ensure geometric feasibility.


Example
=====================

.. code-block::

    assembly = TimberAssembly()

    frame = Frame.worldXY()
    main_beam = Beam(frame, width=0.1, height=0.2, depth=1.0, geometry_type="mesh")
    cross_beam = Beam(frame, width=0.2, height=0.4, depth=1.0, geometry_type="mesh")
    assembly.add_beam(main_beam)
    assembly.add_beam(cross_beam)

    TButtJoint.create(assembly, main_beam, cross_beam)

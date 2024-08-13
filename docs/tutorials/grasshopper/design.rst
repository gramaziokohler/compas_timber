******
Design
******

Design Components help to generate standard Wall structures from Surfaces, using different Options.

.. image:: ../images/gh_design_workflow.png
    :width: 60%
|
Surface Model
^^^^^^^^^^^^^
Creates a Model from a Surface

Inputs:

* `surface` - :code:`Surface` that represents the Wall Dimensions
* `stud_spacing` - :code:`Number`: Spacing between the Studs
* `beam_width` - :code:`Number`: Width of the Beams
* `frame_depth` - :code:`Number`: Depth of the Frame = Height of the Beams
* `stud_direction` - :code:`Vector` or :code:`Line`: Optional, control Stud Direction
* `options` - Surface Model Options Component
* `CreateGeometry` - :code:`Boolean`: Set to True if Joint Geometry should be generated
|

Outputs:

*	`Model` : the resulting Model.
*	`Geometry` : Geometry of the beams and joints.
*   `DebugInfo` : Debug information object in the case of feature or joining errors.

Surface Model Options
^^^^^^^^^^^^^^^^^^^^^
Creates the Options for the Surface Model

Inputs:

* `sheeting_outside` - :code:`Boolean`: True if Sheeting on the outside should be generated
* `sheeting_inside` - :code:`Boolean`: True if Sheeting on the inside should be generated
* `lintel_posts` - :code:`Boolean`: #TODO
* `edge_stud_offset` - :code:`Number`: #TODO
* `custom_dimensions` - Custom Dimensions Component
* `joint_overrides` - #TODO

Outputs:

*	`Options` : the resulting Beam Model Options.

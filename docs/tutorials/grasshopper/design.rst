******
Design
******

Design Components help to generate standard Wall structures from Surfaces, using different Options.

.. image:: ../images/gh_design_workflow.png
    :width: 60%
|
Surface Model
-------------
Creates a Model from a Surface

Inputs:

* `surface` - Surface
...

Outputs:

*	`Model` : the resulting Model.
*	`Geometry` : Geometry of the beams and joints.
*   `DebugInfo` : Debug information object in the case of feature or joining errors.

Surface Model Options
---------------------
Creates the Options for the Surface Model

Inputs:

* `sheeting_outside` - Surface
...

Outputs:

*	`Options` : the resulting Beam Model Options.

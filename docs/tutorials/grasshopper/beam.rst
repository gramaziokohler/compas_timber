****
Beam
****

A :code:`Beam` object represents a linear (straight) timber part with a rectangular cross-section - for example as a stud, rafter, beam, joist etc.
A :code:`Beam` has a local coordinate system, where the X-axis corresponds with the *centerline*, 
Y-axis with the *width* of the cross-section and Z-axis with the *height* of the cross-section. 
The *origin* is located at the start of the centerline.

.. image:: ../images/beam_01png.png
    :width: 40%

A :code:`Beam` can be created from a `Line` or `LineCurve`, or from `Guid` of a `Line` object referenced from an active Rhino document:


.. image:: ../images/beam_02.png
    :width: 30%

|

*	`Centerline` : the centerline of the beam, also called the major axis
* 	`ZVector`: (optional) a vector used to define the rotation of the cross-section around the centerline. 
	Together with the centerline it indicates the plane in which the Z-axis of the beam lies, 
	which is to say that :code:`ZVector` does not have to be perpendicular, but cannot be parallel, to the centerline.  
	If :code:`None` is provided, a default direction will be used:
    
	* 	vector [1,0,0] (X-direction in world coordinates) if centerline is vertical (parallel to Z-direction in world coordinates)
	* 	otherwise vector [0,0,1] (Z-direction in world coordinates)

* 	`Width`: the smaller dimension of the cross-section (by convention)
* 	`Height`: the larger dimension of the cross-section (by convention)
* 	`Category`: (optional) a string as an additional attribute, 
	used later to define joint rules in :code:`JointCategoryRule` component for the :code:`AutomaticJoint` tool.


Once a :code:`Beam` is created, you can preview its shape, coordinate system and extract its geometry and parameters using these components:

.. image:: ../images/beam_04.png
    :width: 40%


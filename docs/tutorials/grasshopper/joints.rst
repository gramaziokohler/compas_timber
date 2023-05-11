******
Joints
******

In COMPAS TIMBER you can connect two beams using one of the three types of joints: :code:`T-Butt`, :code:`L-Butt` and :code:`L-Miter`.  

Joint Topologies 
----------------

The prefixes in the joint names refer to how the two beams are positioned relatively to each other. 
We distinguish four (topological) situations: **I**, **L**, **T** and **X**:

* **I** - a splice, i.e. beams are co-linear and connect at their ends
* **L** - a corner, i.e. two beam meet at their ends at an angle
* **T** - one beam (here called *main beam*) connects with one of its ends along the length of the other (here called *cross beam*)
* **X** - the beams cross each other

    .. image:: ../images/joint_topologies_diagramm.png
        :width: 30%


Joint components
----------------

T-Butt
^^^^^^

In a :code:`T-Butt` joint, one beam (here called *main beam*) connects with one of its ends to the side of the other (here called *cross beam*). 
The side to connect to is selected automatically based on the angles between the main beam and the sides of the cross beam.  

    .. image:: ../images/TButt_diagramm.png
        :width: 50%


L-Butt
^^^^^^

An :code:`L-Butt` joint is similar to the :code:`T-Butt` joint but additionally the cross beam is trimmed with the respective side 
of the main beam to create a clean corner joint.  

    .. image:: ../images/LButt_diagramm.png
        :width: 50%


L-Miter
^^^^^^^

An :code:`L-Miter` joint connects two beams with a planar cut at a bisector of an angle between them.  

    .. image:: ../images/LMiter_diagramm.png
        :width: 50%


AutomaticJoint wizzard
----------------------

Connecting beams can be automated using **JointCategoryRule** and **AutomaticJoints** components:

**JointCategoryRule** component serves to define which joint type should be applied when a beam of the first category (`CatA`) meets a beam of the second category (`CatB`).  

**AutomaticJoints** component does two things: First, it determines if two beams connect and if yes, determines the joint topology (I, L, T or X). 
Then, it assigns the join type to every connecting pair of beams according to the defined rules. 
If the defined joint type has a different topology than the beams, no joint is assigned 
(Example: two beams form a corner (L) but the rule tries to assign a T-Butt joint).

Inputs:

* `Beams`: list of beams. To avoid unintended results, it should be the same list that is later used as an input to **Assembly**.
* `Rules`: rules defined using **JointCategoryRule** components
* `MaxDistance`: (optional) tolerance for finding connecting beams if the centerlines to not intersect exactly but are at a certain distance from each other. Default is 0.000001.

.. image:: ../images/Joints4Categories_diagramm.png
    :width: 50%

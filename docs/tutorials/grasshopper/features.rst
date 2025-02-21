********
Features
********

Features are additional geometric operations on beams:

.. image:: ../images/Features_Axo.png
  :width: 75%

|

Jack Rafter Cut Feature
^^^^^^^^^^^^^^^^^^^^^^^^
.. image:: ../images/Features_JackRafter.png
  :width: 100%

|
**JackRafterCut** feature cuts beam with a plane. The part of the beam lying on the *z-positive* side ofthe plane will be removed.

* `Beam` : the beam to be trimmed
* `Plane` : the plane to trim the beam as a surface

Brep Drill Hole Feature
^^^^^^^^^^^^^^^^^^^^^^^
**BrepDrillHoleFeature** is a boolean operation to subtract a hole from a beam.

* `Beam` : the beam to be drilled
* `Line` : the axis of the hole as a Line
* `Diameter` : the diameter of the hole

Trim Feature
^^^^^^^^^^^^
**TrimFeature** cuts a beam with a *Plane*. The part of the beam lying on the *z-positive* side of the plane will be removed.

* `Beam` : the beam to be trimmed
* `Plane` : the plane to trim the beam as a surface

The output `Feature` is to be used as input for the **Model** component. See :doc:`model`.


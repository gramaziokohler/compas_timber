********************************************************************************
COMPAS TIMBER
********************************************************************************

.. figure:: /_images/compas_timber.png
     :figclass: figure
     :class: figure-img img-fluid


.. rst-class:: lead

COMPAS TIMBER is an open-source package for modeling, designing and fabricating timber frame structures.

COMPAS TIMBER is written in Python and and is a part of the `COMPAS <https://compas.dev/index.html>`__ ecosystem.
It also features an implementation for `Rhinoceros 3D <https://www.rhino3d.com/>`__
as a `Grasshopper <https://www.rhino3d.com/features/#grasshopper>`__ plug-in.

COMPAS TIMBER is an active research project and is being continuously developed at Gramazio Kohler Research at ETH Zurich.
At the current stage, the library encompasses tools for fast and intuitive design of frame structures with simple joints
using custom object classes for beam, joints and assembly entities to maintain parametric and semantic information about the structure.
In the future, it will be expanded to entail interfaces to structural analysis software and specialist timber construction software,
assembly sequencing methods, fabricability checking tools and more.


Dependencies
============

COMPAS TIMBER builts upon the `COMPAS <https://compas.dev/index.html>`__ framework.
It inherits many basic geometry classes like :code:`Point`, :code:`Line`, :code:`Vector` etc. from COMPAS.

For more complex types of geometric objects like *Brep*, it resolves to environment-specific backends.
For example, if the code is run in `Rhinoceros 3D <https://www.rhino3d.com/>`__,
it uses `RhinoCommon SDK <https://developer.rhino3d.com/api/rhinocommon/>`__ to handle *Brep* geometry, and
if the code is run in a python process, it will default to
`OpenCascade <https://www.opencascade.com/open-cascade-technology/>`__ via `COMPAS OCC <https://compas.dev/compas_occ>`__.


Table of Contents
=================

.. toctree::
   :maxdepth: 3
   :titlesonly:

   Introduction <self>
   installation
   api
   examples
   tutorials
   license
   citing


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`

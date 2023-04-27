********************************************************************************
COMPAS TIMBER
********************************************************************************

.. rst-class:: lead

This is the documentation of COMPAS TIMBER - an open-source package for modeling, designing and fabricating timber frame structures.




Dependencies
============

COMPAS TIMBER builts upon the `COMPAS <https://compas.dev/index.html>`__ framework.
It inherits many basic geometry classes like :code:`Point`, :code:`Line`, :code:`Vector` etc. from COMPAS.

For more complex types of geometric objects like *Brep*, it resolves to environment-specific backends. 
For example, if the code is run in `Rhinoceros 3D <https://www.rhino3d.com/>`__, it will rely on this CAD software's SDK to handle *Brep* geometry.
If the code is run in a python process, it will default to OpenCascade via COMPAS OCC.


.. .. figure:: /_images/
     :figclass: figure
     :class: figure-img img-fluid


Table of Contents
=================

.. toctree::
   :maxdepth: 3
   :titlesonly:

   Introduction <self>
   installation
   gettingstarted
   api
   examples
   tutorials
   license
   citing


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`

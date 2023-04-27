Grasshopper plugin
******************

.. .. rst-class:: lead

.. note::
    The following tutorial focusses on the COMPAS TIMBER plugin for `Grasshopper <https://www.rhino3d.com/features/#grasshopper>`__.  
    For help on the COMPAS TIMBER python library, please see :doc:`api`. 

.. note::    
    You can also use the COMPAS TIMBER python library in Grasshopper using the `ghPython componenent <https://developer.rhino3d.com/guides/rhinopython/ghpython-component/>`__.

Grasshopper plugin
==================

**COMPAS TIMBER for Grasshopper** is an easy-to-use tool to design timber frame structures from simple centerline input. 
It provides tools to automate the process of creating timber frame structures with simple joints, 
*bake* the geometry with fibre-aligned box-mapping for texturing/rendering,
add boolean-style features like planar cuts or holes,
and some more.

The plugin is built on top of the COMPAS TIMBER python library and provides additional functionalities that might be useful for design in Grasshopper. 

.. image:: tutorials/images/gh_ct_toolbar.png
    :width: 100%

|
To get an overall idea how to use it, start with :doc:`tutorials/grasshopper/workflow`. 
Then, the following sections explain in detail the concepts and tools:

.. how to add a page to the menu on the left without adding it to the toctree here?

.. toctree::
    :maxdepth: 1
    :titlesonly:

    tutorials/grasshopper/workflow 
    tutorials/grasshopper/beam
    tutorials/grasshopper/attributes
    tutorials/grasshopper/joints
    tutorials/grasshopper/features
    tutorials/grasshopper/assembly
    tutorials/grasshopper/show
    tutorials/grasshopper/utils
    tutorials/grasshopper/examples

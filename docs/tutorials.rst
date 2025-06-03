Grasshopper plugin
******************


**COMPAS Timber for Grasshopper** is an easy-to-use tool to design timber frame structures from simple centerline input.
It provides tools to automate the process of creating timber frame structures with simple joints,
*bake* the geometry with fibre-aligned box-mapping for texturing/rendering,
add boolean-style features like planar cuts or holes,
and some more.

The plugin is built on top of the COMPAS Timber python library and provides additional functionalities that might be useful for design in Grasshopper.

.. image:: tutorials/images/gh_toolbar.png
    :width: 100%


.. note::
    You can also use the COMPAS Timber python library in Grasshopper using the ghPython componenent.
    See COMPAS Timber :doc:`api` and :doc:`examples` for more details.

To get an overall idea how to use it, start with :doc:`tutorials/grasshopper/workflow`.
Then, the following sections explain in detail the concepts and tools:

.. how to add a page to the menu on the left without adding it to the toctree here?

.. toctree::
    :maxdepth: 1
    :titlesonly:

    tutorials/grasshopper/installation
    tutorials/grasshopper/workflow
    tutorials/grasshopper/attributes
    tutorials/grasshopper/beams
    tutorials/grasshopper/design
    tutorials/grasshopper/fabrication
    tutorials/grasshopper/features
    tutorials/grasshopper/joint_rules
    tutorials/grasshopper/model
    tutorials/grasshopper/show
    tutorials/grasshopper/utils
    tutorials/grasshopper/examples
    tutorials/BTLx_contribution_guide

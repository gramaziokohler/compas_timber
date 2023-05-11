********
Workflow
********

To build a timber frame **Assembly**, you need to:

*   create **Beams** 
*   define **Joints** between these beams
*   define other **Features** (optional)  

Based on this, **Assembly** takes care of generating the final geometry of the structure.

.. image:: ../images/workflow_diagramm.png
    :width: 50%

|
|

**Example:**   

.. image:: ../images/workflow_gh_example.png
    :width: 75%


|

.. note::
    
    **Important!**   

    * The order in the list of **Joints** and **Features** matters! For example: if there are two different joints defined for the same pair of beams in the list, the last one will be applied (overrides entries earlier in the list).
    * The **Joints** are processed first, then **Features**.
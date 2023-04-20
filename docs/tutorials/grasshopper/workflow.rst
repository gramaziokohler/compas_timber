********
Workflow
********

To build a timber frame :code:`Assembly`, you need to:

*   create :code:`Beams` 
*   define :code:`Joints` between these beams
*   define other :code:`Features` (optional)  

Based on this, :code:`Assembly` takes care of generating the final geometry of the structure.

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

    * The order in the list of :code:`Joints` and :code:`Features` matters! For example: if there are two different joints defined for the same pair of beams in the list, the last one will be applied (overrides entries earlier in the list).
    * The :code:`Joints` are processed first, then :code:`Features`.
********
Assembly
********

**Assembly** component creates a frame structure made of joined :code:`Beam` objects. 
It connects the beams and adds features based on provided `Joints` (:doc:`joints`) and `Features` (:doc:`features`) definitions.

Geometric operations like cutting, trimming and solid boolean subtractions, which are implied by joints and features, 
may be computationally expensive, and are disabled by default. 
To activate it, set `applyFeatures` to :code:`True`. 
Output parameter `Errors` provides a log of unsuccessful feature-apply operations.


Assembly as such is an abstract object. To visualize it (to visualize the beams in the assembly), 
use the :code:`ShowAssembly` component that returns the *Brep* geometry of the beams.

.. image:: ../images/assembly_01.png
    :width: 50%


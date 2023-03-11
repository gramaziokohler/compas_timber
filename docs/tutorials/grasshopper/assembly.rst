********
Assembly
********

`Assembly` component creates a frame structure made of joined `Beams`. It connects the beams and adds features based on provided `Joints` and `Features` definitions.

Geometric operations like cutting, trimming and solid boolean subtractions, which are implied by joints and features, may be computationally expensive, and are disabled by default. To activate it, set `applyFeatures` to `True`. `Errors` provide a log of unsuccessful feature-apply operations.


Assembly as such is an abstract object. To visualize it (to visualize the beams in the assembly), use the `ShowAssembly` component that returns the _Brep_ geometry of the beams.

.. image:: ../images/assembly_01.png
    :width: 60%


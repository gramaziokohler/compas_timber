*******************************************************************************
Create Joint
*******************************************************************************

.. code-block::

    assembly = TimberAssembly()

    frame = Frame.worldXY()
    beam1 = Beam(frame, width=0.1, height=0.2, depth=1.0, geometry_type="mesh")
    beam2 = Beam(frame, width=0.2, height=0.4, depth=1.0, geometry_type="mesh")
    assembly.add_beam(beam1)
    assembly.add_beam(beam2)

    TButtJoint.create(assembly, beam1, beam2)

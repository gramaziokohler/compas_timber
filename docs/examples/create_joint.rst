*******************************************************************************
Create Joint
*******************************************************************************

.. code-block::

    assembly = TimberAssembly()

    frame = Frame.worldXY()
    main_beam = Beam(frame, width=0.1, height=0.2, depth=1.0, geometry_type="mesh")
    cross_beam = Beam(frame, width=0.2, height=0.4, depth=1.0, geometry_type="mesh")
    assembly.add_beam(main_beam)
    assembly.add_beam(cross_beam)

    TButtJoint.create(assembly, main_beam, cross_beam)

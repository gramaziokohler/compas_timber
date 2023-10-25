"""
the Joint factories take a BTLxJoint class instance, generate the BTLx processes and append them to the BTLxPart instances in the BTLx class instance.

some joints will require combinations of multiple BTLx processes, and some processes will cover multiple joint types.

the factory module should call the BTLxJoint.register_joint(joint type, joint factory) function so that the BTLxJoint class can call specific factory types.

The factory will typically derive the needed parameters from the BTLxJoint instance and the btlx_process will apply them to the individual BTLxParts.

"""

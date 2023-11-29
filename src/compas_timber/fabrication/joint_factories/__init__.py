"""
the Joint factories take a Joint class instance, generate the BTLx processes and append them to the BTLxPart.processes list.

some joints will require combinations of multiple BTLx processes, and some processes will cover multiple joint types.

the factory module should call the BTLx.register_joint(joint type, joint factory) function so that the BTLx class can call specific factory types.

The factory will typically derive the needed parameters from the Joint instance and the joint_factory will apply them to the individual BTLxParts.
"""

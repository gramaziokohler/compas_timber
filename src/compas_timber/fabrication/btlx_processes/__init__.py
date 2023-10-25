"""
the btlx processes apply the btlx processes to the individual BTLxParts

the class should have the following attributes

PROCESS_TYPE a class attribute which matches the btlx process name
self.header_attributes which matches as a dict,
self.process_parameters which describe the geometric parameters of the process


the joint factory calls the process.apply_process()

each process will have specific inputs which can hopefully be derived from the BTLxJoint class, which contains Joint and Beam objects


some joints will require combinations of multiple BTLx processes, and some processes will cover multiple joint types.

the factory module should call the BTLxJoint.register_joint(joint type, joint factory) function so that the BTLxJoint class can call specific factory types.

The factory will typically derive the needed parameters from the BTLxJoint instance and the btlx_process will apply them to the individual BTLxParts.

"""

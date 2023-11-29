"""
the btlx processes apply the btlx processes to the individual BTLxParts

the class should have the following attributes

PROCESS_TYPE a class attribute which matches the btlx process name
self.header_attributes which matches as a dict,
self.process_parameters which describe the geometric parameters of the process


the joint factory calls instantiates a process or processes and appends it or them to the BTLxPart.processes list

each process will have specific inputs which can hopefully be derived from the Joint instance and related BTLxParts


some joints will require combinations of multiple BTLx processes, and some processes will cover multiple joint types.

the factory module should call the BTLx.register_joint(joint type, joint factory) function so that the BTLx class can call specific factory types.

The factory will typically derive the needed parameters from the Joint instance and the joint_factory will apply them to the individual BTLxParts.

"""

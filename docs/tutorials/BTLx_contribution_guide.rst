"""
Processes are BTLx machining steps. Each Joint type generates one or more different processes.

To add a new joint including BTLx process or processes:

1. create the joint module
    -inherits from Joint class.
    -This does not requre generating a geometrical representation.

2. create necessary processes
    -if the process or processes do not exist, generate new modules in the btlx_processes package.
    -new processes should follow the BTLx documentation found here: https://design2machine.com/btlx/btlx_2_1_0.pdf
    -processes are instantiated as generic BTLxProcess instance in a joint_factory method that appends the process to the input BTLxPart.processes list.
    -BTLxProcess is instantiated with BTLxProcess(PROCESS_TYPE, header_attributes, process_params) where:
        -PROCESS_TYPE a class attribute which matches the btlx process name
        -self.header_attributes which matches as a dict,
        -self.process_params which describe the geometric parameters of the process

3. create a joint factory
    -takes a Joint and BTLxParts as input.
    -the factory module should call the BTLxJoint.register_joint(joint type, joint factory) function so that the BTLxJoint class can call specific factory types.
    -the factory can apply multiple processes to a single part
    -the factory will typically derive the needed parameters from the Joint instance and related BTLxParts
    -the factory will instantiate the generic BTLxProcess or processes and append them to the BTLxPart.processes list

4. create import and dependencies
    -add import to this __init__.py file

Mind the reference surfaces used in the BTLx definition
"""

"""
Processes are BTLx machining steps. Each Joint type generates one or more different processes.

To add a new joint including BTLx process or processes:

1. create the joint module
    -inherits from Joint class.
    -This does not requre generating a geometrical representation.

2. create necessary processes
    -if the process or processes do not exist, generate new modules in the btlx_processes package.
    -new processes should follow the BTLx documentation found here: https://design2machine.com/btlx/btlx_2_1_0.pdf
    -processes are instantiated with the apply_process(BTLxPart, BTLxJoint, *args) method that appends the process to the input BTLxPart.processes list.
    -BTLxProcess is instantiated in apply_process method with BTLxProcess(PROCESS_TYPE, header_attributes, process_params) where:
        -PROCESS_TYPE a class attribute which matches the btlx process name
        -self.header_attributes which matches as a dict,
        -self.process_parameters which describe the geometric parameters of the process

3. create a joint factory
    -takes a BTLxJoint as input and calls a specific btlx_joint.apply_process() method for each process for each BTLxPart/Beam used in that joint.
    -The joint factory is called with a factory.apply_processes(BTLxJoint) method which takes a BTLxJoint object as input.
    -the factory module should call the BTLxJoint.register_joint(joint type, joint factory) function so that the BTLxJoint class can call specific factory types.
    -the factory can apply multiple processes to a single part

4. create import and dependencies
    -add import to this __init__.py file

Mind the reference surfaces used in the BTLx definition

"""

from .btlx import BTLx
from .btlx import BTLxProcess
from .btlx import BTLxJoint
from .btlx_processes.btlx_jack_cut import BTLxJackCut
from .btlx_processes.btlx_french_ridge_lap import BTLxFrenchRidgeLap
from .btlx_processes.btlx_lap import BTLxLap
from .joint_factories.l_butt_factory import LButtFactory
from .joint_factories.t_butt_factory import TButtFactory
from .joint_factories.l_miter_factory import LMiterFactory
from .joint_factories.french_ridge_factory import FrenchRidgeFactory
from .joint_factories.x_halflap_factory import XHalfLapFactory

__all__ = [
    "BTLx",
    "BTLxProcess",
    "BTLxJoint",
    "BTLxJackCut",
    "BTLxFrenchRidgeLap",
    "BTLxLap",
    "LButtFactory",
    "TButtFactory",
    "LMiterFactory",
    "FrenchRidgeFactory",
    "XHalfLapFactory",
]

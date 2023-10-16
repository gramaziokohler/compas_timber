"""
Processes are BTLx machining steps. Each Joint type generates one or more different processes.

Each Process type inherits from BTLxProcess and each must have the following:

self.apply_process -> bool      some processes will be created but should not be applied to the part, for example, no process is applied to the crossing beam of a t-Butt. in this case, self.apply_process should be false
self.process_type  -> returns string with process name per https://design2machine.com/btlx/BTLx_2_1_0.xsd
self.header_attributes -> returns dict with process attributes NOTE: pay attention to reference plane ID!
self.process_params -> returns dict with geometric parameters of process
BTLxProcess.register_process(joint_type, process_type) registers the child class for the create() method for specific joint and process types.

To create a new process class, the specific process class, e.g. BTLxJackCut, should inherit fom the parent class BTLxProcess.
Additionally, an instance of the process class should be returned by classmethod BTLxProcess.create(joint, part) using the registered_processes

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from .btlx import BTLx
# from .btlx import BTLxProcess
# from .btlx_jack_cut import BTLxJackCut
# from .btlx_french_ridge_lap import BTLxFrenchRidgeLap

__all__ = [
    "BTLx",
    # # "BTLxProcess",
    # "BTLxJackCut",
    # "BTLxFrenchRidgeLap"
]

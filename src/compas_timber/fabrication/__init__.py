"""
Processes are BTLx machining steps. Each Joint type generates one or two different processes.

Each Process type inherits from BTLxProcess and should have the following:

(attribute) self.process_type = "" -> String that matches the process name in the btlx documentation
(attribute) self.header_attributes = {} -> Dict with Keys and Values matching process attributes
(property or attribute) self.process_params = {} -> Dict with Keys and Values defining geometry of process





"""

# from .btlx_processes.btlx_jack_cut import BTLxJackCut


# __all__ = [
#     "BTLxJackCut",

# ]

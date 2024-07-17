from compas.data import Data


class BTLxProcess(Data):
    """Base class for BTLx processes.

    Attributes
    ----------
    ref_side_index : int
        The reference side, zero-based, index of the beam to be cut. 0-5 correspond to RS1-RS6.
    """

    @property
    def __data__(self):
        return {"ref_side_index": self.ref_side_index}

    def __init__(self, ref_side_index):
        super(BTLxProcess, self).__init__()
        self.ref_side_index = ref_side_index


class OrientationType(object):
    """Enum for the orientation of the cut.

    Attributes
    ----------
    START : int
        The start of the beam is cut away.
    END : int
        The end of the beam is cut away.
    """

    START = 0
    END = 1

from collections import OrderedDict
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxProcess


class BTLxDoubleCut(object):
    """
    Represents a double cut process for timber fabrication.

    Parameters
    ----------
    param_dict : dict
        A dictionary containing the parameters for the BTLx lap process.
    joint_name : str
        The name of the joint. If not provided, the default name is "lap".
    kwargs : dict
        Additional keyword arguments to be added to the object.

    """

    PROCESS_TYPE = "DoubleCut"

    def __init__(self, param_dict, joint_name=None, **kwargs):
        self.apply_process = True
        self.reference_plane_id = param_dict["ReferencePlaneID"]
        self.orientation = param_dict["Orientation"]
        self.start_x = param_dict["StartX"]
        self.start_y = param_dict["StartY"]
        self.angle1 = param_dict["Angle1"]
        self.inclination1 = param_dict["Inclination1"]
        self.angle2 = param_dict["Angle2"]
        self.inclination2 = param_dict["Inclination2"]

        for key, value in param_dict.items():
            setattr(self, key, value)

        for key, value in kwargs.items():
            setattr(self, key, value)

        if joint_name:
            self.name = joint_name
        else:
            self.name = "lap"

    @property
    def header_attributes(self):
        """the following attributes are required for all processes, but the keys and values of header_attributes are process specific."""
        return {
            "Name": self.name,
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": str(self.reference_plane_id + 1),
        }

    @property
    def process_params(self):
        """This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint."""

        if self.apply_process:
            """the following attributes are specific to Lap"""
            od = OrderedDict(
                [
                    ("Orientation", str(self.orientation)),
                    ("StartX", "{:.{prec}f}".format(self.start_x, prec=BTLx.POINT_PRECISION)),
                    ("StartY", "{:.{prec}f}".format(self.start_y, prec=BTLx.POINT_PRECISION)),
                    ("Angle1", "{:.{prec}f}".format(self.angle1, prec=BTLx.ANGLE_PRECISION)),
                    ("Inclination1", "{:.{prec}f}".format(self.inclination1, prec=BTLx.ANGLE_PRECISION)),
                    ("Angle2", "{:.{prec}f}".format(self.angle2, prec=BTLx.ANGLE_PRECISION)),
                    ("Inclination2", "{:.{prec}f}".format(self.inclination2, prec=BTLx.ANGLE_PRECISION))
                ]
            )
            print("param dict", od)
            return od
        else:
            return None

    @classmethod
    def create_process(cls, param_dict, joint_name=None, **kwargs):
        """Creates a lap process from a dictionary of parameters."""
        lap = BTLxDoubleCut(param_dict, joint_name, **kwargs)
        return BTLxProcess(BTLxDoubleCut.PROCESS_TYPE, lap.header_attributes, lap.process_params)

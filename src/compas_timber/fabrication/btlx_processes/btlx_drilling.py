from collections import OrderedDict
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxProcess


class BTLxDrilling(object):
    """
    Represents a drilling process for timber fabrication.

    Parameters
    ----------
    param_dict : dict
        A dictionary containing the parameters for the BTLx lap process.
    joint_name : str
        The name of the joint. If not provided, the default name is "lap".
    kwargs : dict
        Additional keyword arguments to be added to the object.

    """

    PROCESS_TYPE = "Drilling"

    def __init__(self, param_dict, joint_name=None, **kwargs): # joint_name replace by "feature_name"?
        self.apply_process = True
        self.reference_plane_id = param_dict["ReferencePlaneID"]
        self.start_x = param_dict["StartX"]
        self.start_y = param_dict["StartY"]
        self.angle = param_dict["Angle"]
        self.inclination = param_dict["Inclination"]
        self.depth_limited = param_dict["DepthLimited"]
        self.depth = param_dict["Depth"]
        self.diameter = param_dict["Diameter"]

        for key, value in param_dict.items():
            setattr(self, key, value)

        for key, value in kwargs.items():
            setattr(self, key, value)

        if joint_name: # to delete since no joint?
            self.name = joint_name
        else:
            self.name = "drilling" # what instead?

    @property
    def header_attributes(self):
        """the following attributes are required for all processes, but the keys and values of header_attributes are process specific."""
        return {
            "Name": self.name,
            "Process": "yes",
            "Priority": "0",
            "ProcessID": "0",
            "ReferencePlaneID": self.reference_plane_id,
        }

    @property
    def process_params(self):
        """This property is required for all process types. It returns a dict with the geometric parameters to fabricate the joint."""

        if self.apply_process:
            """the following attributes are specific to Drilling"""
            od = OrderedDict(
                [
                    ("StartX", "{:.{prec}f}".format(self.start_x, prec=BTLx.POINT_PRECISION)),
                    ("StartY", "{:.{prec}f}".format(self.start_y, prec=BTLx.POINT_PRECISION)),
                    ("Angle", "{:.{prec}f}".format(self.angle, prec=BTLx.ANGLE_PRECISION)),
                    ("Inclination", "{:.{prec}f}".format(self.inclination, prec=BTLx.ANGLE_PRECISION)),
                    ("DepthLimited", str(self.depth_limited)),
                    ("Depth", "{:.{prec}f}".format(self.depth, prec=BTLx.POINT_PRECISION)),
                    ("Diameter", "{:.{prec}f}".format(self.diameter, prec=BTLx.POINT_PRECISION)),
                ]
            )
            return od
        else:
            return None

    @classmethod
    def create_process(cls, param_dict, joint_name=None, **kwargs): # joint_name replace by "feature_name"?
        """Creates a drilling process from a dictionary of parameters."""
        drilling = BTLxDrilling(param_dict, joint_name, **kwargs)
        return BTLxProcess(BTLxDrilling.PROCESS_TYPE, drilling.header_attributes, drilling.process_params)

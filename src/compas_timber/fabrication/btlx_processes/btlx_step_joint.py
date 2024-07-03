from collections import OrderedDict
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxProcess


class BTLxStepJoint(object):
    """
    Represents a step joint process for timber fabrication.

    Parameters
    ----------
    param_dict : dict
        A dictionary containing the parameters for the BTLx Step Joint process.
    joint_name : str
        The name of the joint. If not provided, the default name is "step joint".
    kwargs : dict
        Additional keyword arguments to be added to the object.

    """

    PROCESS_TYPE = "StepJoint"

    def __init__(self, param_dict, joint_name=None, **kwargs):
        self.apply_process = True
        self.reference_plane_id = param_dict["ReferencePlaneID"]
        self.orientation = param_dict["Orientation"]
        self.start_x = param_dict["StartX"]
        self.strut_inclination = param_dict["StrutInclination"]
        self.step_depth = param_dict["StepDepth"]
        self.hell_depth = param_dict["HeelDepth"]
        self.step_shape = param_dict["StepShape"]
        self.tenon = param_dict["Tenon"]
        self.tenon_width = param_dict["TenonWidth"]
        self.tenon_height = param_dict["TenonHeight"]

        for key, value in param_dict.items():
            setattr(self, key, value)

        for key, value in kwargs.items():
            setattr(self, key, value)

        if joint_name:
            self.name = joint_name
        else:
            self.name = "step joint"

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
            """the following attributes are specific to Step Joint"""
            od = OrderedDict(
                [
                    ("Orientation", str(self.orientation)),
                    ("StartX", "{:.{prec}f}".format(self.start_x, prec=BTLx.POINT_PRECISION)),
                    ("StrutInclination", "{:.{prec}f}".format(self.strut_inclination, prec=BTLx.ANGLE_PRECISION)),
                    ("StepDepth", "{:.{prec}f}".format(self.step_depth, prec=BTLx.POINT_PRECISION)),
                    ("HeelDepth", "{:.{prec}f}".format(self.hell_depth, prec=BTLx.POINT_PRECISION)),
                    ("StepShape", str(self.step_shape)),
                    ("Tenon", str(self.tenon)),
                    ("TenonWidth", "{:.{prec}f}".format(self.tenon_width, prec=BTLx.POINT_PRECISION)),
                    ("TenonHeight", "{:.{prec}f}".format(self.tenon_height, prec=BTLx.POINT_PRECISION)),
                ]
            )
            print("param dict", od)
            return od
        else:
            return None

    @classmethod
    def create_process(cls, param_dict, joint_name=None, **kwargs):
        """Creates a Step Joint process from a dictionary of parameters."""
        step_joint = BTLxStepJoint(param_dict, joint_name, **kwargs)
        return BTLxProcess(BTLxStepJoint.PROCESS_TYPE, step_joint.header_attributes, step_joint.process_params)
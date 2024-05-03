from collections import OrderedDict
from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxProcess


class BTLxText(object):
    """
    Represents an engraving process of a text for timber fabrication.

    Parameters
    ----------
    param_dict : dict
        A dictionary containing the parameters for the BTLx lap process.
    joint_name : str
        The name of the joint. If not provided, the default name is "lap".
    kwargs : dict
        Additional keyword arguments to be added to the object.

    """

    PROCESS_TYPE = "Text"

    def __init__(self, param_dict, joint_name=None, **kwargs): # joint_name replace by "feature_name"?
        self.apply_process = True
        self.reference_plane_id = param_dict["ReferencePlaneID"]
        self.start_x = param_dict["StartX"]
        self.start_y = param_dict["StartY"]
        self.angle = param_dict["Angle"]
        self.alignment_vertical = param_dict["AlignmentVertical"]
        self.alignment_horizontal = param_dict["AlignmentHorizontal"]
        self.alignment_multiline = param_dict["AlignmentMultiline"]
        self.stacked_marking = param_dict["StackedMarking"]
        self.text_height_auto = param_dict["TextHeightAuto"]
        self.text_height = param_dict["TextHeight"]
        self.text = param_dict["Text"]

        for key, value in param_dict.items():
            setattr(self, key, value)

        for key, value in kwargs.items():
            setattr(self, key, value)

        if joint_name:
            self.name = joint_name
        else:
            self.name = "text_engraving"

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
            """the following attributes are specific to a text engraving"""
            od = OrderedDict(
                [
                    ("StartX", "{:.{prec}f}".format(self.start_x, prec=BTLx.POINT_PRECISION)),
                    ("StartY", "{:.{prec}f}".format(self.start_y, prec=BTLx.POINT_PRECISION)),
                    ("Angle", "{:.{prec}f}".format(self.angle, prec=BTLx.ANGLE_PRECISION)),
                    ("AlignmentVertical", str(self.alignment_vertical)),
                    ("AlignmentHorizontal", str(self.alignment_horizontal)),
                    ("AlignmentMultiline", str(self.alignment_multiline)),
                    ("StackedMarking", bool(self.stacked_marking)),
                    ("TextHeightAuto", bool(self.text_height_auto)),
                    ("TextHeight", "{:.{prec}f}".format(self.text_height, prec=BTLx.POINT_PRECISION)),
                    ("Text", str(self.text)),

                ]
            )
            return od
        else:
            return None

    @classmethod
    def create_process(cls, param_dict, joint_name=None, **kwargs):
        """Creates a text process from a dictionary of parameters."""
        text = BTLxText(param_dict, joint_name, **kwargs)
        return BTLxProcess(BTLxText.PROCESS_TYPE, text.header_attributes, text.process_params)

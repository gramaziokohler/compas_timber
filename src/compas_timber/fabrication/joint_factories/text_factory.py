from compas_timber.fabrication import BTLx
from compas_timber.fabrication import BTLxText

class TextFactory(object):
    """
    Factory class for creating Text engraving.
    """

    def __init__(self):
        pass

    @staticmethod
    def get_engraving_position(part):
        """Finds the optimal parameter on the line for the text engraving process."""
        [part.intersections.append(i) for i in {0, 1} if i not in part.intersections]
        all_points = sorted(part.intersections)
        print("intersections", all_points)
        max_length = 0
        optimal_midpoint = 0.5
        for i in range(len(all_points) - 1):
            seg_length = all_points[i+1] - all_points[i]
            if seg_length > max_length:
                max_length = seg_length
                optimal_midpoint = (all_points[i] + all_points[i+1]) / 2
        print("Optimal midpoint: ", optimal_midpoint*part.length, "optimal parameter", optimal_midpoint)
        return float(optimal_midpoint*part.length)

    @staticmethod
    def get_text_engraving_params(part):
        """Returns the text engraving parameters for the BTLx part."""
        return {
            "ReferencePlaneID": 1, #default face
            "StartX": TextFactory.get_engraving_position(part),
            "StartY": part.width/2, #always set it to the middle of the beam
            "Angle": 0.0,
            "AlignmentVertical": "center",
            "AlignmentHorizontal": "center",
            "AlignmentMultiline": "center",
            "TextHeight": 20.0,
            # "Text": part.beam.attributes["airModule_no"]
            "Text": "Hello you 023"
        }

    @classmethod
    def apply_processings(cls, part):
        """
        Apply processings to the joint and parts.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.joint.Joint`
            The joint object.
        parts : dict
            A dictionary of the BTLxParts connected by this joint, with part keys as the dictionary keys.

        Returns
        -------
        None

        """

        if part.processings:
            ref_plane_id = part.processings[0].header_attributes.get("ReferencePlaneID", 1)
        else:
            ref_plane_id = "1"
        params_dict = TextFactory.get_text_engraving_params(part)
        params_dict["ReferencePlaneID"] = ref_plane_id
        part.processings.append(BTLxText.create_process(params_dict, "Text"))

BTLx.register_feature("TextID", TextFactory)


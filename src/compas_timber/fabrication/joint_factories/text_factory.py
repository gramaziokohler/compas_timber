from compas_timber.parts import BrepSubtraction

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
        intersections = set(part.intersections)
        intersections.update({0, 1})  # Ensure 0 and 1 are included
        all_intersections = sorted(intersections)

        max_length = 0
        optimal_parameter = 0.5
        for i in range(len(all_intersections) - 1):
            seg_length = all_intersections[i+1] - all_intersections[i]
            if seg_length > max_length:
                max_length = seg_length
                optimal_parameter = (all_intersections[i] + all_intersections[i+1]) / 2

        optimal_parameter = 0.5 if optimal_parameter in {0, 1} else optimal_parameter
        optimal_position = optimal_parameter * part.length
        return optimal_position

    @staticmethod
    def get_text_engraving_params(part):
        """Returns the text engraving parameters for the BTLx part."""
        return {
            "ReferencePlaneID": 1, #default face
            "StartX": TextFactory.get_engraving_position(part) - (7*20.0)/2, #7=number of characters in the ID
            "StartY": part.width/2 - 10., #manually center it since text is not centered in easybeam
            "Angle": 0.0,
            "AlignmentVertical": "bottom", #default(bottom) in easybeam
            "AlignmentHorizontal": "left", #default(left) in easybeam
            "AlignmentMultiline": "left",   #default(left) in easybeam
            "TextHeight": 15.0,
            "Text": part.ID
        }

    def add_features(self):
        """Adds the trimming plane to the main beam (no features for the cross beam).

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        pass
        # assert self.main_beam and self.cross_beam  # should never happen
        # if self.features:
        #     self.main_beam.remove_features(self.features)
        # cutting_plane = None
        # try:
        #     cutting_plane = self.get_main_cutting_plane()[0]
        # except AttributeError as ae:
        #     raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        # except Exception as ex:
        #     raise BeamJoinningError(beams=self.beams, joint=self, debug_info=str(ex))

        # self.features = []
        # if self.birdsmouth:
        #     if self.calc_params_birdsmouth():
        #         self.main_beam.add_features(BrepSubtraction(self.bm_sub_volume))
        #         self.features.append(BrepSubtraction(self.bm_sub_volume))


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


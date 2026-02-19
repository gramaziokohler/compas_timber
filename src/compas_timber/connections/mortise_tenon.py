from compas_timber.fabrication import Mortise
from compas_timber.fabrication import Tenon
from compas_timber.fabrication import TenonShapeType

from .joint import Joint
from .utilities import beam_ref_side_incidence


class MortiseTenonJoint(Joint):
    """Base class for mortise-tenon joints.

    This class stores shared parameter handling, serialization, and feature creation
    helpers used by mortise-tenon joint variants.
    """

    @property
    def __data__(self):
        data = super(MortiseTenonJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["rotation"] = self.rotation
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["shape"] = self.shape
        data["shape_radius"] = self.shape_radius
        return data

    # fmt: off
    def __init__(
        self,
        main_beam,
        cross_beam,
        start_y=None,
        start_depth=None,
        rotation=None,
        length=None,
        width=None,
        height=None,
        shape=None,
        shape_radius=None,
        **kwargs
    ):
        super(MortiseTenonJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)

        self.start_y = start_y
        self.start_depth = start_depth
        self.rotation = rotation
        self.length = length
        self.width = width
        self.height = height
        self.shape = shape
        self.shape_radius = shape_radius

        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.cross_beam, self.main_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def tenon_shape(self):
        if self.shape == 0:
            shape_type = TenonShapeType.AUTOMATIC
        elif self.shape == 1:
            shape_type = TenonShapeType.SQUARE
        elif self.shape == 2:
            shape_type = TenonShapeType.ROUND
        elif self.shape == 3:
            shape_type = TenonShapeType.ROUNDED
        elif self.shape == 4:
            shape_type = TenonShapeType.RADIUS
        else:
            raise ValueError("Invalid tenon shape index. Please provide a valid index between 0 and 4.")
        return shape_type

    def _update_unset_values(self):
        """Updates and sets default property values if they are not provided."""
        width, height = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)

        self.start_y = self.start_y or 0.0
        self.start_depth = self.start_depth or 0.0
        self.rotation = self.rotation or 0.0
        self.length = self.length or height
        self.width = self.width or width / 2
        self.height = self.height or width / 2
        self.shape = self.shape or 2  # Default shape: ROUND
        self.shape_radius = self.shape_radius or width / 4

    def _clear_features(self):
        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)
            self.features = []

    def _create_tenon_feature(self):
        return Tenon.from_plane_and_beam(
            plane=self.cross_beam.ref_sides[self.cross_beam_ref_side_index],
            beam=self.main_beam,
            start_y=self.start_y,
            start_depth=self.start_depth,
            rotation=self.rotation,
            length=self.length,
            width=self.width,
            height=self.height,
            shape=self.tenon_shape,
            shape_radius=self.shape_radius,
            ref_side_index=self.main_beam_ref_side_index,
        )

    def _create_mortise_feature(self, main_feature):
        return Mortise.from_frame_and_beam(
            frame=main_feature.frame_from_params_and_beam(self.main_beam),
            beam=self.cross_beam,
            start_depth=0.0,  # TODO: to be updated once housing is implemented
            length=main_feature.length,
            width=main_feature.width,
            depth=main_feature.height,
            shape=main_feature.shape,
            shape_radius=main_feature.shape_radius,
            ref_side_index=self.cross_beam_ref_side_index,
        )

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model[self.main_beam_guid]
        self.cross_beam = model[self.cross_beam_guid]

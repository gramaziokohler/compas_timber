import abc

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import Mortise
from compas_timber.fabrication import Tenon
from compas_timber.fabrication import TenonShapeType

from .joint import Joint
from .utilities import beam_ref_side_incidence


class MortiseTenonJoint(Joint, abc.ABC):
    """Base class for mortise-tenon joints.

    This is an abstract class and should not be instantiated directly.

    This class stores shared parameter handling, serialization, and feature creation
    helpers used by mortise-tenon joint variants.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    start_y : float
        Start position of the tenon along the y-axis of the main beam.
    start_depth : float
        Depth of the tenon from the surface of the main beam.
    rotation : float
        Rotation of the tenon around the main beam's axis.
    length : float
        Length of the tenon along the main beam.
    width : float
        Width of the tenon.
    height : float
        Height of the tenon.
    shape : int
        The shape of the tenon, represented by an integer index:
        0: AUTOMATIC, 1: SQUARE, 2: ROUND, 3: ROUNDED, 4: RADIUS.
    shape_radius : float
        The radius used to define the shape of the tenon, if applicable.
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    main_beam_guid : str
        GUID of the main beam.
    cross_beam_guid : str
        GUID of the cross beam.
    start_y : float
        Start position of the tenon along the y-axis of the main beam.
    start_depth : float
        Depth of the tenon from the surface of the main beam.
    rotation : float
        Rotation of the tenon around the main beam's axis.
    length : float
        Length of the tenon along the main beam.
    width : float
        Width of the tenon.
    height : float
        Height of the tenon.
    shape : int
        The shape of the tenon, represented by an integer index:
        0: AUTOMATIC, 1: SQUARE, 2: ROUND, 3: ROUNDED, 4: RADIUS.
    shape_radius : float
        The radius used to define the shape of the tenon, if applicable.
    features : list
        List of features or machining processings applied to the elements.
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

    def get_main_extension(self):
        """Return the start/end extension lengths for the main beam.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        cutting_plane = None
        try:
            cutting_plane = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
            main_width = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)[0]
            offset = self.height or main_width / 2  # in case height is not set this is the default value set when adding features
            cutting_plane.translate(-cutting_plane.normal * offset)
            start_main, end_main = self.main_beam.extension_to_plane(cutting_plane)
        except AttributeError as ae:
            debug_geometries = [cutting_plane] if cutting_plane is not None else None
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=debug_geometries)
        return start_main, end_main

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model[self.main_beam_guid]
        self.cross_beam = model[self.cross_beam_guid]

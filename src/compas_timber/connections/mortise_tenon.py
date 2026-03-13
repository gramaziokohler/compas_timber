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
    tenon_shape : str
        Shape of the tenon. One of :class:`~compas_timber.fabrication.TenonShapeType`: AUTOMATIC, SQUARE, ROUND, ROUNDED, RADIUS.
        Defaults to ``TenonShapeType.ROUND``.
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
    tenon_shape : str
        Shape of the tenon. One of :class:`~compas_timber.fabrication.TenonShapeType`: AUTOMATIC, SQUARE, ROUND, ROUNDED, RADIUS.
    shape_radius : float
        The radius used to define the shape of the tenon, if applicable.
    features : list
        List of features or machining processings applied to the elements.
    """

    @property
    def __data__(self):
        data = super(MortiseTenonJoint, self).__data__
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["rotation"] = self.rotation
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["tenon_shape"] = self.tenon_shape
        data["shape_radius"] = self.shape_radius
        return data

    # fmt: off
    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        start_y=None,
        start_depth=None,
        rotation=None,
        length=None,
        width=None,
        height=None,
        tenon_shape=None,
        shape_radius=None,
        **kwargs
    ):
        super(MortiseTenonJoint, self).__init__(elements=(main_beam, cross_beam), **kwargs)
        self.start_y = start_y
        self.start_depth = start_depth
        self.rotation = rotation
        self.length = length
        self.width = width
        self.height = height
        self.tenon_shape = tenon_shape
        self.shape_radius = shape_radius

        self.features = []

        if self.main_beam and self.cross_beam:
            self._set_unset_attributes()

    @property
    def main_beam(self):
        return self.element_a
    
    @property
    def cross_beam(self):
        return self.element_b

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

    def _set_unset_attributes(self):
        """Updates and sets default property values if they are not provided."""
        assert self.cross_beam and self.main_beam
        width, height = self.main_beam.get_dimensions_relative_to_side(self.main_beam_ref_side_index)

        self.start_y = self.start_y or 0.0
        self.start_depth = self.start_depth or 0.0
        self.rotation = self.rotation or 0.0
        self.length = self.length or height
        self.width = self.width or width / 2
        self.height = self.height or width / 2
        self.tenon_shape = self.tenon_shape or TenonShapeType.ROUND
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
            cutting_plane.translate(-cutting_plane.normal * self.height)
            start_main, end_main = self.main_beam.extension_to_plane(cutting_plane)
        except AttributeError as ae:
            raise BeamJoiningError(beams=self.elements, joint=self, debug_info=str(ae), debug_geometries=[cutting_plane])
        return start_main, end_main


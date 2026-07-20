import abc
from functools import wraps
from typing import Optional

from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import PlanarSurface
from compas.geometry import Plane
from compas.geometry import Transformation
from compas.geometry import Vector
from compas_model.elements import Element
from compas_model.elements import reset_computed


class UserReferencePlaneCollection(Data):
    """The user reference planes attached to a single :class:`TimberElement`, for use in BTLx processings.

    Planes are stored keyed by their BTLx integer ``id_`` (an ``unsignedInt >= 100`` per the BTLx
    spec), each mapping to a :class:`compas.geometry.Frame` expressed relative to the owning
    element's ``ref_frame`` (BTLx's ``PartRef``: "The ReferencePlane refers to the PartRef").

    This collection should not be queried or modified directly. Use the owning `TimberElement`'s
    `add_user_ref_plane()`, `get_user_ref_plane()`, and `remove_user_ref_plane()` instead.

    ``id_`` values handed out by :meth:`add` come from a counter that only ever moves forward, so a
    removed ``id_`` is never reissued, even if planes are added and removed repeatedly.

    A new collection always starts empty.

    """

    def __init__(self):
        super(UserReferencePlaneCollection, self).__init__()
        self._frames_by_id = {}
        self._next_id = 100

    def __repr__(self):
        return "UserReferencePlaneCollection({!r})".format(self._frames_by_id)

    def __len__(self):
        return len(self._frames_by_id)

    def __iter__(self):
        return iter(self._frames_by_id.items())

    @property
    def __data__(self):
        # JSON object keys are always strings, so the ids need to round-trip through str <-> int explicitly.
        return {"planes": {str(id_): frame for id_, frame in self._frames_by_id.items()}, "next_id": self._next_id}

    @classmethod
    def __from_data__(cls, data):
        collection = cls()
        collection._frames_by_id = {int(id_): frame for id_, frame in data["planes"].items()}
        collection._next_id = data["next_id"]
        return collection

    def add(self, local_frame: Frame, id_: int = None) -> int:
        """Store ``local_frame`` under ``id_``, auto-assigning the next free id if not given.

        Parameters
        ----------
        local_frame : :class:`compas.geometry.Frame` or :class:`compas.geometry.Plane`
            The plane, expressed relative to the owning element's ``ref_frame``. A ``Plane`` is
            converted to a ``Frame`` via :meth:`Frame.from_plane`.
        id_ : int, optional
            The BTLx integer id to assign to this plane. Must be a unique integer >= 100.
            If None, the next auto-assigned id is used (see class docstring).

        Returns
        -------
        int
            The id assigned to this plane.

        """
        if isinstance(local_frame, Plane):
            local_frame = Frame.from_plane(local_frame)

        if id_ is not None:
            if type(id_) is not int:
                raise TypeError("BTLx reference plane ids must be integers.")
            if id_ < 100:
                raise ValueError("BTLx reference plane ids must be >= 100.")
            if id_ in self._frames_by_id:
                raise ValueError("A reference plane with id {} already exists. Call remove() first.".format(id_))
        else:
            id_ = self._next_id

        self._frames_by_id[id_] = local_frame
        self._next_id = max(self._next_id, id_ + 1)
        return id_

    def get(self, id_: int) -> Optional[Frame]:
        """Return the frame stored under ``id_``, or None if no such plane exists.

        Use `TimberElement.get_user_ref_plane()` instead of calling this directly.
        """
        return self._frames_by_id.get(id_)

    def remove(self, id_: int) -> None:
        """Remove the plane stored under ``id_``, if any."""
        self._frames_by_id.pop(id_, None)


def reset_timber_attrs(f):
    """Decorator to reset cached timber-specific attributes."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        self: TimberElement = args[0]
        self._blank = None
        self._ref_frame = None
        self._geometry = None  # from Element
        return f(*args, **kwargs)

    return wrapper


class TimberElement(Element, abc.ABC):
    """Base class for all timber elements.

    This is an abstract class and should not be instantiated directly.

    Parameters
    ----------
    frame : :class:`compas.geometry.Frame`, optional
        The frame representing the element's local coordinate system in its hierarchical context.
        Defaults to ``None``, in which case the world coordinate system is used.
    length : float
        Length of the timber element.
    width : float
        Width of the timber element.
    height : float
        Height of the timber element.
    features : list[:class:`~compas_timber.fabrication.Feature`], optional
        List of features to apply to this element.
    user_ref_planes : :class:`UserReferencePlaneCollection`, optional
        The BTLx user reference planes attached to this element. Populated internally on
        deserialization; use :meth:`add_user_ref_plane` to add planes otherwise.
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    frame : :class:`compas.geometry.Frame`
        The coordinate system of this element in model space.
        This property may be different from the constructor parameter if the element belongs to a model hierarchy.
    is_beam : bool
        True if the element is a beam.
    is_plate : bool
        True if the element is a plate.
    is_group_element : bool
        True if the element can be used as container for other elements.
    features : list[:class:`~compas_timber.parts.Feature`]
        A list of features applied to the element.
    geometry : :class:`compas.geometry.Geometry`
        The geometry of the element in the model's global coordinates.

    """

    @property
    def __data__(self):
        data = {}
        data["frame"] = self.frame
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["features"] = [f for f in self.features if not f.is_joinery]  # type: ignore
        data["user_ref_planes"] = self._user_ref_planes
        data.update(self.attributes)
        return data

    def __init__(self, frame, length, width, height, features=None, user_ref_planes=None, **kwargs):
        super().__init__(transformation=Transformation.from_frame(frame), features=features)
        self._user_ref_planes = user_ref_planes if user_ref_planes is not None else UserReferencePlaneCollection()
        self.attributes = {}
        self.attributes.update(kwargs)
        self.length = length
        self.width = width
        self.height = height
        self._blank = None
        self._ref_frame = None
        self.debug_info = []

    @reset_computed
    @reset_timber_attrs
    def _reset_computed_dummy(self):
        """Dummy method to trigger reset_computed decorator."""
        pass

    def reset_computed_properties(self):
        """Reset all computed/cached properties."""
        self._reset_computed_dummy()

    def clear_model_dependent_cache(self):
        """Clear cached attributes that depend on the element's position in the model hierarchy.

        Preserves model-independent caches such as ``_elementgeometry``, features,
        and blank extensions.
        """
        self._modeltransformation = None
        self._modelgeometry = None
        self._aabb = None
        self._obb = None
        self._collision_mesh = None
        self._blank = None
        self._ref_frame = None
        self._geometry = None

    @property
    def is_beam(self):
        return False

    @property
    def is_plate(self):
        return False

    @property
    def is_group_element(self):
        # NOTE: I left this in for now, but in the new compas_model, any element can be a container/parent.
        return False

    @property
    def features(self):
        # type: () -> list[BTLxProcessing]
        return self._features

    @features.setter
    @reset_computed
    def features(self, features):
        self._features = features

    @reset_timber_attrs
    def transform(self, transformation):
        # override to reset timber-specific cached attributes
        super().transform(transformation)

    @property
    def geometry(self):
        """The geometry of the element in the model's global coordinates."""
        if self._geometry is None:
            self._geometry = self.compute_modelgeometry()
        return self._geometry

    # ========================================================================
    # Geometry computation methods
    # ========================================================================

    def compute_modeltransformation(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.transformation
        return super().compute_modeltransformation()

    def compute_modelgeometry(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.elementgeometry.transformed(self.transformation)
        return super().compute_modelgeometry()

    # ========================================================================
    # Feature management & Modification methods
    # ========================================================================

    def remove_blank_extension(self):
        """Remove blank extension from the element.

        This method is intended to be overridden by subclasses.
        """
        pass

    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        self.remove_features()
        self.remove_blank_extension()
        self.debug_info = []

    @reset_computed
    @reset_timber_attrs
    def add_feature(self, feature):
        # type: (BTLxProcessing) -> None
        """Adds one or more features to the beam.

        Parameters
        ----------
        feature : :class:`~compas_timber.fabrication.BTLxProcessing`)
            The feature to be added.

        """
        self._features.append(feature)  # type: ignore

    @reset_computed
    @reset_timber_attrs
    def add_features(self, features):
        # type: (BTLxProcessing | list[BTLxProcessing]) -> None
        """Adds one or more features to the beam.

        Parameters
        ----------
        features : :class:`~compas_timber.fabrication.BTLxProcessing` | list(:class:`~compas_timber.fabrication.BTLxProcessing`)
            The feature or features to be added described as a BTLxProcessing or a list of BTLxProcessings.

        """
        if not isinstance(features, list):
            features = [features]
        self._features.extend(features)  # type: ignore

    @reset_computed
    @reset_timber_attrs
    def remove_features(self, features=None):
        # type: (None | BTLxProcessing | list[BTLxProcessing]) -> None
        """Removes a feature from the beam.

        Parameters
        ----------
        features : :class:`~compas_timber.fabrication.BTLxProcessing` | list(:class:`~compas_timber.fabrication.BTLxProcessing`) | None
            The feature or features to be removed described as a BTLxProcessing or a list of BTLxProcessings.
            If None, all features will be removed.

        """
        if features is None:
            self._features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self._features = [f for f in self._features if f not in features]

    def transformation_to_local(self):
        """Compute the transformation to local coordinates of this element
        based on its position in the spatial hierarchy of the model.

        Returns
        -------
        :class:`compas.geometry.Transformation`

        """
        # type: () -> Transformation
        return self.modeltransformation.inverted()

    ########################################################################
    # BTLx properties
    ########################################################################

    @property
    def ref_frame(self):
        # type: () -> Frame
        # See: https://design2machine.com/btlx/BTLx_2_2_0.pdf
        """
        Reference frame for machining processings according to BTLx standard.
        The origin is at the bottom far corner of the element.
        The ref_frame is always in model coordinates.
        """
        if not self._ref_frame:
            self._ref_frame = Frame(
                self.blank.points[1], Vector.from_start_end(self.blank.points[1], self.blank.points[2]), Vector.from_start_end(self.blank.points[1], self.blank.points[7])
            )
        return self._ref_frame

    @property
    def ref_sides(self):
        # type: () -> tuple[Frame, Frame, Frame, Frame, Frame, Frame]
        # See: https://design2machine.com/btlx/BTLx_2_2_0.pdf
        rs1_point = self.ref_frame.point
        rs2_point = rs1_point + self.ref_frame.yaxis * self.height
        rs3_point = rs1_point + self.ref_frame.yaxis * self.height + self.ref_frame.zaxis * self.width
        rs4_point = rs1_point + self.ref_frame.zaxis * self.width
        rs5_point = rs1_point
        rs6_point = rs1_point + self.ref_frame.xaxis * self.blank_length + self.ref_frame.yaxis * self.height
        return (
            Frame(rs1_point, self.ref_frame.xaxis, self.ref_frame.zaxis, name="RS_1"),
            Frame(rs2_point, self.ref_frame.xaxis, -self.ref_frame.yaxis, name="RS_2"),
            Frame(rs3_point, self.ref_frame.xaxis, -self.ref_frame.zaxis, name="RS_3"),
            Frame(rs4_point, self.ref_frame.xaxis, self.ref_frame.yaxis, name="RS_4"),
            Frame(rs5_point, self.ref_frame.zaxis, self.ref_frame.yaxis, name="RS_5"),
            Frame(rs6_point, self.ref_frame.zaxis, -self.ref_frame.yaxis, name="RS_6"),
        )

    @property
    def ref_edges(self):
        # type: () -> tuple[Line, Line, Line, Line]
        # so tuple is not created every time
        ref_sides = self.ref_sides
        return (
            Line(ref_sides[0].point, ref_sides[0].point + ref_sides[0].xaxis * self.blank_length, name="RE_1"),
            Line(ref_sides[1].point, ref_sides[1].point + ref_sides[1].xaxis * self.blank_length, name="RE_2"),
            Line(ref_sides[2].point, ref_sides[2].point + ref_sides[2].xaxis * self.blank_length, name="RE_3"),
            Line(ref_sides[3].point, ref_sides[3].point + ref_sides[3].xaxis * self.blank_length, name="RE_4"),
        )

    def side_as_surface(self, side_index):
        # type: (int) -> compas.geometry.PlanarSurface
        """Returns the requested side of the beam as a parametric planar surface.

        Parameters
        ----------
        side_index : int
            The index of the reference side to be returned. 0 to 5.

        """
        # TODO: maybe this should be the default representation of the ref sides?
        ref_side = self.ref_sides[side_index]
        if side_index in (0, 2):  # top + bottom
            xsize = self.blank_length
            ysize = self.width
        elif side_index in (1, 3):  # sides
            xsize = self.blank_length
            ysize = self.height
        elif side_index in (4, 5):  # ends
            xsize = self.width
            ysize = self.height
        return PlanarSurface(xsize, ysize, frame=ref_side, name=ref_side.name)

    def front_side(self, ref_side_index):
        # type: (int) -> Frame
        """Returns the next side after the reference side, following the right-hand rule with the thumb along the beam's frame x-axis.
        This method does not consider the start and end sides of the beam (RS5 & RS6).

        Parameters
        ----------
        ref_side_index : int
            The index of the reference side to which the front side should be calculated.

        Returns
        -------
        frame : :class:`~compas.geometry.Frame`
            The frame of the front side of the beam relative to the reference side.
        """
        return self.ref_sides[(ref_side_index + 1) % 4]

    def back_side(self, ref_side_index):
        # type: (int) -> Frame
        """Returns the previous side before the reference side, following the right-hand rule with the thumb along the beam's frame x-axis.
        This method does not consider the start and end sides of the beam (RS5 & RS6).

        Parameters
        ----------
        ref_side_index : int
            The index of the reference side to which the back side should be calculated.

        Returns
        -------
        frame : :class:`~compas.geometry.Frame`
            The frame of the back side of the beam relative to the reference side.
        """
        return self.ref_sides[(ref_side_index - 1) % 4]

    def opp_side(self, ref_side_index):
        # type: (int) -> Frame
        """Returns the the side that is directly across from the reference side, following the right-hand rule with the thumb along the beam's frame x-axis.
        This method does not consider the start and end sides of the beam (RS5 & RS6).

        Parameters
        ----------
        ref_side_index : int
            The index of the reference side to which the opposite side should be calculated.

        Returns
        -------
        frame : :class:`~compas.geometry.Frame`
            The frame of the opposite side of the beam relative to the reference side.
        """
        return self.ref_sides[(ref_side_index + 2) % 4]

    def get_dimensions_relative_to_side(self, ref_side_index):
        # type: (int) -> tuple[float, float]
        """Returns the dimensions of a timber element with respect to the Y- axis and Normal of the given reference side.

        Parameters
        ----------
        ref_side_index : int
            The index of the reference side to which the dimensions should be calculated.

        Returns
        -------
        tuple(float, float)
            Y-axis dimension, Normal direction dimension.
                - Y-axis dimension: The element dimension along y-axis of reference side.
                - Normal dimension: The element dimension normal to the reference side.
        """
        if ref_side_index in [1, 3]:
            return self.height, self.width
        return self.width, self.height

    ########################################################################
    # User Reference Planes
    ########################################################################

    @property
    def user_ref_planes(self):
        """The BTLx user reference planes attached to this element.

        This collection should not be queried or modified directly. Use `add_user_ref_plane()`,
        `get_user_ref_plane()`, and `remove_user_ref_plane()` instead.

        Returns
        -------
        :class:`UserReferencePlaneCollection`
        """
        return self._user_ref_planes

    def add_user_ref_plane(self, frame: Frame, id_: int = None) -> int:
        """Add a named reference plane to this element.

        By default, the BTLx ``id_`` is auto-assigned from a monotonically increasing counter
        starting at 100 (first plane → 100, second → 101, …), and a removed plane's id is never
        reissued.

        Parameters
        ----------
        frame : :class:`compas.geometry.Frame`
            The plane expressed in model (world) coordinates. It is converted to and stored relative
            to :attr:`ref_frame` (BTLx's ``PartRef``), matching how BTLx itself defines a custom
            reference plane.
        id_ : int, optional
            The BTLx integer id to assign to this plane. This should be a unique integer >= 100.
            If None, the id is auto-assigned (see above).

        Returns
        -------
        int
            The BTLx integer id assigned to this plane (>= 100).

        """
        local_frame = frame.transformed(Transformation.from_frame(self.ref_frame).inverted())
        return self._user_ref_planes.add(local_frame, id_)

    def get_user_ref_plane(self, id_: int) -> Optional[Frame]:
        """Retrieve the frame of a reference plane stored under ``id_``.

        The returned frame is transformed to model coordinates, so it can be used directly in the model space.

        Parameters
        ----------
        id_ : int
            The BTLx integer id of the reference plane to retrieve.

        Returns
        -------
        :class:`compas.geometry.Frame` or None
            The frame of the reference plane with the given id, transformed to model coordinates,
            or None if no such plane exists.
        """
        local_frame = self._user_ref_planes.get(id_)
        if local_frame is None:
            return None
        return local_frame.transformed(Transformation.from_frame(self.ref_frame))

    def remove_user_ref_plane(self, id_: int):
        """Remove the reference plane stored under ``id_``.

        Parameters
        ----------
        id_ : int
            The BTLx integer id of the reference plane to remove.
        """
        self._user_ref_planes.remove(id_)

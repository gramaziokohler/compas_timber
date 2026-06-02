from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional
from typing import Union

if TYPE_CHECKING:
    from compas.datastructures import Mesh  # noqa: F401
    from compas.geometry import Brep  # noqa: F401

    from compas_timber.panel_features import PanelFeature  # noqa: F401

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.tolerance import TOL
from compas_model.elements import Element
from compas_model.elements import reset_computed

from compas_timber.errors import FeatureApplicationError
from compas_timber.panel_features import PanelFeatureType
from compas_timber.utils import get_plate_geometry_outlines_from_brep
from compas_timber.utils import get_polyline_normal_vector
from compas_timber.utils import polylines_from_brep_face



from .plate_geometry import PlateGeometry


class PanelType(object):
    """Constants for different types of panels.

    Attributes
    ----------
    WALL : str
        Constant for wall panels.
    FLOOR : str
        Constant for floor panels.
    ROOF : str
        Constant for roof panels.
    GENERIC : str
        Constant for generic panels.
    """

    WALL = "wall"
    FLOOR = "floor"
    ROOF = "roof"
    GENERIC = "generic"


class Panel(Element):
    """Represents a timber panel element (wall, floor, roof, etc.).

    Serves as container for beams, plates, and other related elements and groups them together to form a panel.
    A panel is often a single unit of prefabricated timber element.
    It is often referred to as an enveloping body.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this panel.
    length : float
        Length of the panel.
    width : float
        Width of the panel.
    thickness : float
        Thickness of the panel.
    local_outline_a: :class:`~compas.geometry.Polyline`, optional
        A polyline representing the principal outline of this panel.
    local_outline_b: :class:`~compas.geometry.Polyline`, optional
        A polyline representing the associated outline of this panel.
    openings : list[:class:`~compas.geometry.Polyline`], optional
        A list of Polyline objects representing openings in this panel.
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this panel.
    length : float
        Length of the panel.
    width : float
        Width of the panel.
    height : float
        Height (thickness) of the panel.
    thickness : float
        Thickness of the panel.
    planes : tuple (:class:`~compas.geometry.Plane`, :class:`~compas.geometry.Plane`)
        The two main planes of the panel (bottom and top).
    normal : :class:`~compas.geometry.Vector`
        The normal vector of the panel.
    edge_planes : dict[int, :class:`~compas.geometry.Plane`]
        The edge planes of the panel by edge index.
    is_group_element : bool
        Always True for panels as they can contain other elements.

    """

    @property
    def __data__(self):
        data = super().__data__
        data["frame"] = Frame.from_transformation(data.pop("transformation"))
        data["length"] = self.length
        data["width"] = self.width
        data["thickness"] = self.height
        data["features"] = [f for f in self.features if f.panel_feature_type != PanelFeatureType.CONNECTION_INTERFACE]
        data.update(self.attributes)
        data.update(self.plate_geometry.__data__)
        return data

    def __init__(
        self,
        frame: Frame,
        length: float,
        width: float,
        thickness: float,
        local_outline_a: Optional[Polyline] = None,
        local_outline_b: Optional[Polyline] = None,
        openings: Optional[list[Polyline]] = None,
        type: Optional[str] = None,
        **kwargs,
    ):
        super(Panel, self).__init__(transformation=frame.to_transformation(), **kwargs)  # NOTE: Element wants a transfomration, not a frame
        local_outline_a = local_outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        local_outline_b = local_outline_b or Polyline([Point(p[0], p[1], thickness) for p in local_outline_a.points])
        self.plate_geometry = PlateGeometry(local_outline_a=local_outline_a, local_outline_b=local_outline_b, openings=openings)

        self.length = length
        self.width = width
        self.height = thickness
        self.type = type or PanelType.GENERIC
        self.attributes = {}
        self.attributes.update(kwargs)
        self.exterior_layer=None
        self.core_layer=None
        self.interior_layer=None
        self._planes = None

    def __repr__(self) -> str:
        return "Panel(name={}, {}, {}, {:.3f})".format(self.name, Frame.from_transformation(self.transformation), self.outline_a, self.thickness)

    def __str__(self) -> str:
        return "Panel(name={}, {}, {}, {:.3f})".format(self.name, Frame.from_transformation(self.transformation), self.outline_a, self.thickness)

    @property
    def geometry(self):
        return self.modelgeometry

    @geometry.setter
    def geometry(self, geometry):
        # overriding to please linter but this shouldn't be setable directly.
        raise AttributeError("Geometry is a computed property and cannot be set directly. To modify the geometry, change the outlines, thickness, or features of the panel.")

    @property
    def outlines(self):
        return (self.outline_a, self.outline_b)

    @property
    def outline_a(self):
        return self.plate_geometry.outline_a.transformed(self.modeltransformation)

    @property
    def outline_b(self):
        return self.plate_geometry.outline_b.transformed(self.modeltransformation)

    @property
    def thickness(self):
        return self.height

    @property
    def planes(self):
        if not self._planes:
            planes = (Plane.worldXY(), Plane(Point(0, 0, self.thickness), Vector(0, 0, 1)))
            self._planes = (planes[0].transformed(self.modeltransformation), planes[1].transformed(self.modeltransformation))
        return self._planes

    @property
    def normal(self):
        return Vector(0, 0, 1).transformed(self.modeltransformation)

    @property
    def edge_planes(self):
        # TODO: transform to global?
        return {i: plane.transformed(self.modeltransformation) for i, plane in self.plate_geometry.edge_planes.items()}

    def set_extension_plane(self, edge_index: int, plane: Plane):
        """Sets an extension plane for a specific edge of the plate. This is called by plate joints."""
        self.plate_geometry.set_extension_plane(edge_index, plane.transformed(self.transformation_to_local()))

    def apply_edge_extensions(self):
        """adjusts segments of the outlines to lay on the edge planes created by plate joints."""
        self.plate_geometry.apply_edge_extensions()

    def remove_blank_extension(self, edge_index: Optional[int] = None):
        """Removes any extension plane for the given edge index."""
        self.plate_geometry.remove_blank_extension(edge_index)

    def define_layer(self, start_level:float, end_level:float, name:Optional[str]=None, parent_layer:Optional[Layer]=None)->None:
        """Adds a layer to the panel. Layers are used to group features and agents within the panel.
        Parameters
        ----------
        start_level : float
            The starting level of the layer, measured from the ``outline_a`` face.
        end_level : float
            The ending level of the layer, measured from the ``outline_a`` face.
        name : str, optional
            The name of the layer.
        parent_layer : :class:`~compas_timber.panel_features.Layer`, optional
            The parent layer of the new layer. used when defining sublayers. If None, the new layer is a top-level layer.


        Returns
        -------
        :class:`~compas_timber.panel_features.Layer`
            The created layer object.
        """
        if self._layers is None:
            self._layers = []
        layer_index = len(self._layers)
        parent_layer = parent_layer or self
        layer = Layer.from_panel_and_range(parent_layer, start_level, end_level, name=name, layer_index=layer_index)
        self._layers.append(layer)
        return layer

    def define_core_layer(self, start:float, end:float) -> Layer:
        """Defines a core layer in the panel. The core layer is centered within the panel and has the specified thickness.
        Parameters
        ----------
        core_thickness : float
            The thickness of the core layer.
        name : str, optional
            The name of the core layer.
        Returns
        -------
        :class:`~compas_timber.panel_features.Layer`
            The created core layer object.
        """
        if start < 0 or end > self.thickness or start >= end:
            raise ValueError("Invalid core layer range. Start and end must be within the panel thickness and start must be less than end.")
        self.exterior_layer = Layer.from_panel_and_range(self, 0, start, name="Exterior Layer")
        self.core_layer = Layer.from_panel_and_range(self, start, end, name="Core Layer")
        self.interior_layer = Layer.from_panel_and_range(self, end, self.thickness, name="Interior Layer")

    @property
    def features(self) -> list[PanelFeature]:
        return self._features

    @property
    def interfaces(self):
        """list[:class:`~compas_timber.panel_features.PanelConnectionInterface`]: The interfaces associated with this panel."""
        return [f for f in self.features if f.panel_feature_type == PanelFeatureType.CONNECTION_INTERFACE]

    @reset_computed
    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        self.plate_geometry.reset()  # reset outline_a and outline_b
        self._features = []
        self.debug_info = []

    @reset_computed
    def remove_features(self, features: Optional[Union[PanelFeature, list[PanelFeature]]] = None) -> None:
        """Removes features from the element.

        Parameters
        ----------
        features : :class:`~compas_timber.panel_features.PanelFeature` | list[:class:`~compas_timber.panel_features.PanelFeature`], optional
            The features to be removed. If None, all features will be removed.

        """
        if features is None:
            self._features = []
        else:
            feature_list = features if isinstance(features, list) else [features]
            self._features = [f for f in self.features if f not in feature_list]

    @property
    def is_group_element(self):
        return True
        # ==========================================================================

    #  Implementation of abstract methods
    # ==========================================================================

    def compute_aabb(self, inflate: float = 0.0) -> Box:
        """Computes the Axis Aligned Bounding Box (AABB) of the element.

        Parameters
        ----------
        inflate : float, optional
            Offset of box to avoid floating point errors.

        Returns
        -------
        :class:`~compas.geometry.Box`
            The AABB of the element.

        """
        vertices = self.outline_a.points + self.outline_b.points
        box = Box.from_points(vertices)
        box.xsize += inflate
        box.ysize += inflate
        box.zsize += inflate
        return box

    def compute_obb(self, inflate: float = 0.0) -> Box:
        """Computes the Oriented Bounding Box (OBB) of the element.

        Returns
        -------
        :class:`compas.geometry.Box`
            The OBB of the element.

        """

        obb = self.plate_geometry.compute_aabb(inflate)
        obb.transform(self.modeltransformation)
        return obb

    def compute_collision_mesh(self) -> Mesh:
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.obb.to_mesh()

    def compute_modeltransformation(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.transformation
        return super().compute_modeltransformation()  # type: ignore

    def compute_modelgeometry(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.elementgeometry.transformed(self.transformation)  # type: ignore
        return super().compute_modelgeometry()  # type: ignore

    def transformation_to_local(self):
        """Compute the transformation from model space to local element space."""
        return self.modeltransformation.inverse()

    def compute_elementgeometry(self, include_features: bool = True) -> Brep:
        """Compute the geometry of the element.

        Parameters
        ----------
        include_features : bool, optional
            If ``True``, include the features in the computed geometry.
            If ``False``, return only the plate shape.

        Returns
        -------
        :class:`compas.datastructures.Mesh` | :class:`compas.geometry.Brep`

        """

        # TODO: consider if Brep.from_curves(curves) is faster/better
        plate_geo = self.plate_geometry.compute_shape()
        if include_features:
            for feature in self._features:
                try:
                    plate_geo = feature.apply(plate_geo, self)
                except FeatureApplicationError as error:
                    self.debug_info.append(error)
        return plate_geo

    @classmethod
    def from_outlines(cls, outline_a: Polyline, outline_b: Polyline, openings: Optional[list[Polyline]] = None, **kwargs):
        """
        Constructs a Panel from two polyline outlines. to be implemented to instantialte Plates and Panels.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            A polyline representing the principal outline of the panel geometry in parent space.
        outline_b : :class:`~compas.geometry.Polyline`
            A polyline representing the associated outline of the panel geometry in parent space.
            This should have the same number of points as outline_a.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of openings to be added to the panel geometry.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Panel`
            A Panel object representing the panel geometry with the given outlines.
        """
        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b, openings)
        kwargs.update(args)
        return cls(**kwargs)

    @classmethod
    def from_outline_thickness(cls, outline: Polyline, thickness: float, vector: Optional[Vector] = None, openings: Optional[list[Polyline]] = None, **kwargs):
        """
        Constructs a Plate from a polyline outline and a thickness.
        The outline is the top face of the plate_geometry, and the thickness is the distance to the bottom face.

        Parameters
        ----------
        outline : :class:`~compas.geometry.Polyline`
            A polyline representing the outline of the plate geometry.
        thickness : float
            The thickness of the plate geometry.
        vector : :class:`~compas.geometry.Vector`, optional
            The direction of the thickness vector. If None, the thickness vector is determined from the outline.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of polyline openings to be added to the plate geometry.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Panel`
            A Panel object representing the panel geometry with the given outline and thickness.
        """
        # this ensure the plate geometry can always be computed
        if TOL.is_zero(thickness):
            thickness = TOL.absolute

        offset_vector = get_polyline_normal_vector(outline, vector)  # gets vector perpendicular to outline
        offset_vector *= thickness
        outline_b = Polyline(outline).translated(offset_vector)
        return cls.from_outlines(outline, outline_b, openings=openings, **kwargs)

    @classmethod
    def from_face_thickness(cls, brep: Brep, thickness: float, vector: Optional[Vector] = None, **kwargs):
        """Creates a panel from a single-face brep.

        Parameters
        ----------
        brep : :class:`~compas.geometry.Brep`
            A single-face brep representing the panel surface.
        thickness : float
            The thickness of the panel.
        vector : :class:`~compas.geometry.Vector`, optional
            The vector in which the panel is extruded.
        **kwargs : dict, optional
            Additional keyword arguments.
            These are passed to the :class:`~compas_timber.elements.Panel` constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Panel`
            A Panel object representing the panel with the given brep and thickness.
        """

        if len(brep.faces) > 1:
            raise ValueError("Can only use single-face breps to create a Panel. This brep has {}".format(len(brep.faces)))
        face = brep.faces[0]
        outer_polyline, inner_polylines = polylines_from_brep_face(face)
        return cls.from_outline_thickness(outer_polyline, thickness, vector=vector, openings=inner_polylines, **kwargs)

    @classmethod
    def from_brep(cls, brep: Brep, **kwargs):
        """Creates a panel from a brep by automatically detecting two parallel faces.

        This method identifies the two main faces of the brep using topological analysis
        (edge counts and adjacency) and uses them as the top and bottom faces of the panel.

        Parameters
        ----------
        brep : :class:`~compas.geometry.Brep`
            The brep representing the panel geometry. Must have at least 2 parallel faces.
        **kwargs : dict, optional
            Additional keyword arguments.
            These are passed to the :class:`~compas_timber.elements.Panel` constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Panel`
            A Panel object created from the two parallel faces of the brep.
        """
        if len(brep.faces) < 2:
            raise ValueError("Brep must have at least 2 faces. This brep has {}".format(len(brep.faces)))
        outline_a, outline_b, openings = get_plate_geometry_outlines_from_brep(brep)
        return cls.from_outlines(outline_a, outline_b, openings=openings, **kwargs)



class Layer(Panel):
    """A resolved cross-section layer that *is* a :class:`~compas_timber.elements.Panel`.

    Each ``Layer`` is created by
    :meth:`~timber_design.populators.PanelPopulatorConfig.create_layers` from a
    :class:`LayerConfig`.  It extends :class:`~compas_timber.elements.Panel`
    with agent tracking and tree-structure bookkeeping.

    Since ``Layer`` inherits from ``Panel``, all panel geometry is accessed
    directly: ``layer.outline_a``, ``layer.outline_b``, ``layer.thickness``,
    ``layer.planes``, etc.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
    length, width, thickness : float
    local_outline_a, local_outline_b : :class:`~compas.geometry.Polyline`, optional
    name : str, optional
    agents : list, optional
    layer_index : int, optional

    Attributes
    ----------
    agents : list
        Agent instances registered on this layer.
    layer_index : int or None
        Zero-based ordinal position in the flat layer list.
    parent_layer : :class:`Layer` or None
        Parent layer in the cross-section tree.
    sublayer_list : list[:class:`Layer`]
        Ordered child layers.
    """

    def __init__(
        self,
        frame,
        length,
        width,
        thickness,
        local_outline_a=None,
        local_outline_b=None,
        type=None,
        name=None,
        agents=None,
        layer_index=None,
        **kwargs,
    ):
        super().__init__(
            frame,
            length,
            width,
            thickness,
            local_outline_a=local_outline_a,
            local_outline_b=local_outline_b,
            type=type,
            **kwargs,
        )
        self.name = name  # Panel.name setter → self._name
        self.agents = agents if agents is not None else []
        self.layer_index = layer_index
        self.parent_layer = None
        self.sublayer_list = []

    def __repr__(self):
        return "Layer with layer_index({})".format(self.layer_index)

    def __str__(self):
        return "Layer(name={}, layer_index={}, position={}, thickness={})".format(self.name, self.layer_index, self.frame.point[2], self.thickness)

    @classmethod
    def from_panel_and_range(
        cls,
        panel,
        range_a: float,
        range_b: float,
        name: Optional[str] = None,
        layer_index: Optional[int] = None,
        agent_configs: Optional[list] = None,
    ) -> "Layer":
        """Create a layer by slicing *panel* to a Z range and attaching agents.

        Parameters
        ----------
        panel : :class:`compas_timber.elements.Panel`
            Source panel to slice.
        range_a : float
            Layer start, measured from the ``outline_a`` face.
        range_b : float
            Layer end, measured from the ``outline_a`` face.
        name : str, optional
        layer_index : int, optional
        agent_configs : list[:class:`~timber_design.populators.LayerAgentConfig`], optional
            Configs whose agents are instantiated on the new layer.  Their beam
            widths are expected to be resolved already; this method calls
            :meth:`~LayerAgentConfig.get_agent_from_layer` without a
            ``standard_beam_width``.

        Returns
        -------
        :class:`Layer`
        """
        if range_a:
            offset = range_a / panel.thickness
            frame_outline_a = Polyline([pt_a * (1.0 - offset) + pt_b * offset for pt_a, pt_b in zip(panel.outline_a.points, panel.outline_b.points)])
        else:
            frame_outline_a = panel.outline_a

        offset = range_b / panel.thickness
        frame_outline_b = Polyline([pt_a * (1.0 - offset) + pt_b * offset for pt_a, pt_b in zip(panel.outline_a.points, panel.outline_b.points)])

        layer = cls.from_outlines(frame_outline_a, frame_outline_b)
        layer.name = name
        layer.layer_index = layer_index
        for agent_config in agent_configs or []:
            layer.agents.append(agent_config.get_agent_from_layer(layer))
        return layer

    def iter_subtree(self):
        """Yield this layer and all descendants depth-first."""
        yield self
        for child in self.sublayer_list:
            yield from child.iter_subtree()

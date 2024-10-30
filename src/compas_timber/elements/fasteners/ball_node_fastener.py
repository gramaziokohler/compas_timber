from compas_model.elements import reset_computed
from compas_timber.utils import intersection_line_line_param
from compas.geometry import Sphere
from compas.geometry import Cylinder
from compas.geometry import Box
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Brep
from compas.geometry.intersections import intersection_sphere_line
from compas_timber.elements import DrillFeature
from compas_timber.elements import BrepSubtraction
from compas_timber.elements import CutFeature
from compas_timber.elements.fasteners.fastener import Fastener



class BallNodeFastener(Fastener):
    """
    A class to represent timber fasteners (screws, dowels, brackets).

    Parameters
    ----------
    elements : list(:class:`~compas_timber.parts.Element`)
        The elements that are connected with this fastener.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this fastener.
    elements : list(:class:`~compas_timber.parts.Element`)
        The elements that are connected with this fastener.

    """

    @property
    def __data__(self):
        data = super(Fastener, self).__data__

        return data

    def __init__(self, elements,thickness = 10, holes = 6, strut_length = 100, ball_diameter = 50, **kwargs):
        super(BallNodeFastener, self).__init__(elements, **kwargs)
        self.elements = elements if isinstance(elements, list) else [elements]
        self.thickness = thickness
        self.holes = holes
        self.strut_length = strut_length
        self.ball_diameter = ball_diameter
        self.features = []
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []
        self.test = []

    def __repr__(self):
        # type: () -> str
        element_str = ["{} {}".format(element.__class__.__name__, element.key) for element in self.elements]
        return "Fastener({})".format(", ".join(element_str))

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def is_fastener(self):
        return True

    @property
    def shape(self):
        # type: () -> Brep

        ends = []
        points = intersection_line_line_param(self.elements[0].centerline, self.elements[1].centerline)
        cpt = None
        if points[0][0] is not None:
            cpt = (points[0][0])
            if points[0][1] > 0.5:
                ends.append("end")
            else:
                ends.append("start")

        for beam in self.elements[1::]:
            points = intersection_line_line_param(self.elements[0].centerline, beam.centerline)
            if points[0][0] is not None and points[1][0] is not None:
                cpt = cpt + points[1][0]
                if points[1][1] > 0.5:
                    ends.append("end")
                else:
                    ends.append("start")
        cpt = cpt*(1.0/len(self.elements))

        geometry = Brep.from_sphere(Sphere(self.ball_diameter/2, point= cpt))
        cut_sphere = Sphere(self.strut_length, point= cpt)
        feat_dict = {}
        for beam, end in zip(self.elements, ends):
            print("BEAM", beam.key)
            feat_dict[beam.key] = []
            cut_pts = intersection_sphere_line([cut_sphere.base, cut_sphere.radius], beam.centerline)
            if cut_pts:
                """ trim beam ends"""
                cut_pt = cut_pts[0] if beam.midpoint.distance_to_point(cut_pts[0])<beam.midpoint.distance_to_point(cut_pts[1]) else cut_pts[1]
                cut_plane = Plane(cut_pt, beam.centerline.direction) if end == "end" else Plane(cut_pt, -beam.centerline.direction)
                beam.add_feature(CutFeature(cut_plane))
                feat_dict[beam.key].append((cut_plane))

                """ add strut to connect beam to ball node"""
                cylinder = Cylinder(self.thickness, self.strut_length, Frame.from_plane(cut_plane))
                cylinder.translate(cylinder.axis.direction * (self.strut_length / 2.0))
                geometry += Brep.from_cylinder(cylinder)

                """ add plate to connect to beam"""
                plate_frame = Frame(cut_pt, beam.frame.xaxis, beam.frame.zaxis) if end == "start" else Frame(cut_pt, -beam.frame.xaxis, beam.frame.zaxis)
                plate = Box(beam.height*self.holes/4.0, beam.height, self.thickness, plate_frame)
                plate.translate(plate_frame.xaxis * (beam.height*self.holes/8.0))
                plate = Brep.from_box(plate)

                """ add drill holes to plate and beam"""
                y_offset = beam.height/6.0
                for _ in range(2):
                    drill_start = plate_frame.point + (plate_frame.zaxis * (-beam.width/2.0)) + (plate_frame.yaxis * y_offset)
                    for _ in range(self.holes/2):
                        drill_start += (plate_frame.xaxis * (beam.height/3.0))
                        drill_line = Line.from_point_direction_length(drill_start, plate_frame.zaxis, beam.width)
                        drill = DrillFeature(drill_line, 10, beam.width)
                        beam.add_feature(drill)

                        mill = BrepSubtraction(plate)
                        beam.add_feature(mill)
                        drillinder = Brep.from_cylinder(Cylinder.from_line_and_radius(drill_line, 5))
                        feat_dict[beam.key].append((drillinder))
                        plate -= drillinder
                    y_offset = -beam.height/6.0
                geometry += plate
            # print(feat_dict)
            self.test.append(feat_dict)
        return geometry

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    def __str__(self):
        element_str = ["{} {}".format(element.__class__.__name__, element.key) for element in self.elements]
        return "Fastener connecting {}".format(", ".join(element_str))

    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    def compute_geometry(self):
        # type: (bool) -> compas.geometry.Brep
        """Compute the geometry of the fastener.

        Returns
        -------
        :class:`compas.geometry.Brep`

        """
        return self.shape

    def compute_aabb(self, inflate=0.0):
        # type: (float) -> compas.geometry.Box
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
        raise NotImplementedError

    def compute_obb(self, inflate=0.0):
        # type: (float | None) -> compas.geometry.Box
        """Computes the Oriented Bounding Box (OBB) of the element.

        Parameters
        ----------
        inflate : float
            Offset of box to avoid floating point errors.

        Returns
        -------
        :class:`compas.geometry.Box`
            The OBB of the element.

        """
        raise NotImplementedError

    def compute_collision_mesh(self):
        # type: () -> compas.datastructures.Mesh
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.shape.to_mesh()

    # ==========================================================================
    # Alternative constructors
    # ==========================================================================


    # ==========================================================================
    # Features
    # ==========================================================================

    @reset_computed
    def add_features(self, features):
        # type: (Feature | list[Feature]) -> None
        """Adds one or more features to the fastener.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be added.

        """
        if not isinstance(features, list):
            features = [features]
        self.features.extend(features)  # type: ignore

    @reset_computed
    def remove_features(self, features=None):
        # type: (None | Feature | list[Feature]) -> None
        """Removes a feature from the fastener.

        Parameters
        ----------
        feature : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be removed. If None, all features will be removed.

        """
        if features is None:
            self.features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self.features = [f for f in self.features if f not in features]

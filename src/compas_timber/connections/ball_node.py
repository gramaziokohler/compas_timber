from compas.geometry import Frame

from compas_timber.elements import BallNodeFastener
from compas_timber.elements import CutFeature
from compas_timber.elements import MillVolume
from compas_timber.elements import DrillFeature
from compas_timber.elements import BrepSubtraction
from compas_timber.elements.fasteners.fastener import Fastener
from compas_timber.utils import intersection_line_line_param
from compas.geometry import Brep
from compas.geometry import Sphere
from compas.geometry import Cylinder
from compas.geometry import Box
from compas.geometry import Plane
from compas.geometry import Line
from compas.geometry import intersection_sphere_line


from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology


class BallNodeJoint(Joint):
    """Represents a ball node type joint which joins the ends of multiple beams,
    trimming the main beam.

    Please use `BallNodeJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    beams :  list(:class:`~compas_timber.parts.Beam`)
        The beams to be joined.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    beam_keys : list(str)
        The keys of the beams.
    features : list(:class:`~compas_timber.parts.Feature`)
        The features created by this joint.
    joint_type : str
        A string representation of this joint's type.

    """

    GH_ARGS = {"beams": None, "thickness": 10, "holes": 6, "strut_length": 100, "ball_diameter": 50}

    def __init__(self, *beams, **kwargs):
        super(BallNodeJoint, self).__init__( **kwargs)
        self._elements = beams
        self.thickness = kwargs.get("thickness", 10)
        self.plate_holes = kwargs.get("holes", 6)
        self.strut_length = kwargs.get("strut_length", 100)
        self.ball_diameter = kwargs.get("ball_diameter", 50)
        self.beam_keys = [str(beam.guid) for beam in beams]
        self.features = []
        self.joint_type = "BallNode"
        self.fastener = BallNodeFastener()

    @property
    def elements(self):
        return self._elements

    @property
    def interactions(self):
        for beam in self.beams:
            yield (beam, self.fastener, self)

    @classmethod
    def create(cls, model, beams, **kwargs):
        """Creates an instance of this joint and creates the new connection in `model`.

        `beams` are expected to have been added to `model` before calling this method.

        This code does not verify that the given beams are adjacent and/or lie in a topology which allows connecting
        them. This is the responsibility of the calling code.

        A `ValueError` is raised if `beams` contains less than two `Beam` objects.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the beams and this joing belong.
        beams : list(:class:`~compas_timber.parts.Beam`)
            A list containing two beams that whould be joined together

        Returns
        -------
        :class:`compas_timber.connections.Joint`
            The instance of the created joint.

        """


        joint = cls(*beams, **kwargs)
        model.add_element(joint.fastener)
        for interaction in joint.interactions:
             _ = model.add_interaction(*interaction)
        return joint

    def add_element(self, element):
        self._elements.append(element)

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        return

    def add_features(self):
        ends = []
        beams = list(self.beams)
        points = intersection_line_line_param(beams[0].centerline, beams[1].centerline)
        cpt = None
        if points[0][0] is not None:
            cpt = (points[0][0])
            if points[0][1] > 0.5:
                ends.append("end")
            else:
                ends.append("start")

        for beam in list(beams)[1::]:
            points = intersection_line_line_param(beams[0].centerline, beam.centerline)
            if points[0][0] is not None and points[1][0] is not None:
                cpt = cpt + points[1][0]
                if points[1][1] > 0.5:
                    ends.append("end")
                else:
                    ends.append("start")
        cpt = cpt*(1.0/len(beams))

        geometry = Brep.from_sphere(Sphere(self.ball_diameter/2, point= cpt))
        cut_sphere = Sphere(self.strut_length, point= cpt)
        feat_dict = {}
        for beam, end in zip(beams, ends):
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
                plate = Box(beam.height*self.plate_holes/4.0, beam.height, self.thickness, plate_frame)
                plate.translate(plate_frame.xaxis * (beam.height*self.plate_holes/8.0))
                plate = Brep.from_box(plate)

                """ add drill holes to plate and beam"""
                y_offset = beam.height/6.0
                for _ in range(2):
                    drill_start = plate_frame.point + (plate_frame.zaxis * (-beam.width/2.0)) + (plate_frame.yaxis * y_offset)
                    for _ in range(self.plate_holes/2):
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
            # self.test.append(feat_dict)
        self.fastener.geometry = geometry

import math
from collections import OrderedDict

from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Cylinder
from compas.geometry import Vector
from compas.geometry import Polyline
from compas.geometry import Point
from compas.geometry import intersection_line_line
from compas.geometry import intersection_plane_plane_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import distance_segment_segment_points
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import OrientationType

from compas.data import json_dump


class SimpleScarf(BTLxProcessing):

    PROCESSING_NAME = "SimpleScarf" # type : ignore

    @property
    def __data__(self):
        data = super(SimpleScarf, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["length"] = self.length
        data["depth_ref_side"] = self.depth_ref_side
        data["depth_opp_side"] = self.depth_opp_side
        data["num_drill_hole"] = self.num_drill_hole
        data["drill_hole_diam_1"] = self.drill_hole_diam_1
        data["drill_hole_diam_2"] = self.drill_hole_diam_2
        return data

    # fmt: off
    def __init__(
        self,
        orientation = OrientationType.START,
        start_x: float=0.0,
        length: float=200.0,
        depth_ref_side: float=20.0,
        depth_opp_side: float=20.0,
        num_drill_hole: int=0,
        drill_hole_diam_1: float=20.0,
        drill_hole_diam_2: float=20.0,
        **kwargs
    ):
        super(SimpleScarf, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._length = None
        self._depth_ref_side = None
        self._depth_opp_side = None
        self._num_drill_hole = None
        self._drill_hole_diam_1 = None
        self._drill_hole_diam_2 = None

        self.orientation = orientation
        self.start_x = start_x
        self.length = length
        self.depth_ref_side = depth_ref_side
        self.depth_opp_side = depth_opp_side
        self.num_drill_hole = num_drill_hole
        self.drill_hole_diam_1 = drill_hole_diam_1
        self.drill_hole_diam_2 = drill_hole_diam_2

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return SimpleScarfParams(self)

    @property
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, orientation):
        if orientation not in [OrientationType.START, OrientationType.END]:
            raise ValueError("Orientation must be either OrientationType.START or OrientationType.END.")
        self._orientation = orientation

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, start_x):
        if start_x < -100000.0 or start_x > 100000.0:
            raise ValueError("StartX must be between -100000.0 and 100000.0.")
        self._start_x = start_x

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if length <= 0.0 or length > 50000.0:
            raise ValueError("Length must be between 0.0 and 50000.0.")
        self._length = length

    @property
    def depth_ref_side(self):
        return self._depth_ref_side

    @depth_ref_side.setter
    def depth_ref_side(self, depth_ref_side):
        if depth_ref_side < 0.0 or depth_ref_side > 50000.0:
            raise ValueError("DepthRefSide must be between 0.0 and 50000.0.")
        self._depth_ref_side = depth_ref_side

    @property
    def depth_opp_side(self):
        return self._depth_opp_side

    @depth_opp_side.setter
    def depth_opp_side(self, depth_opp_side):
        if depth_opp_side < 0.0 or depth_opp_side > 50000.0:
            raise ValueError("DepthOppSide must be between 0.0 and 50000.0.")
        self._depth_opp_side = depth_opp_side

    @property
    def num_drill_hole(self):
        return self._num_drill_hole

    @num_drill_hole.setter
    def num_drill_hole(self, num_drill_hole):
        if num_drill_hole < 0 or num_drill_hole > 2:
            raise ValueError("NumDrillHole must be between 0 and 2.")
        self._num_drill_hole = num_drill_hole

    @property
    def drill_hole_diam_1(self):
        return self._drill_hole_diam_1

    @drill_hole_diam_1.setter
    def drill_hole_diam_1(self, drill_hole_diam_1):
        if drill_hole_diam_1 <= 0.0 or drill_hole_diam_1 > 1000.0:
            raise ValueError("DrillHoleDiam1 must be between 0.0 and 1000.0.")
        self._drill_hole_diam_1 = drill_hole_diam_1

    @property
    def drill_hole_diam_2(self):
        return self._drill_hole_diam_2

    @drill_hole_diam_2.setter
    def drill_hole_diam_2(self, drill_hole_diam_2):
        if drill_hole_diam_2 <= 0.0 or drill_hole_diam_2 > 1000.0:
            raise ValueError("DrillHoleDiam2 must be between 0.0 and 1000.0.")
        self._drill_hole_diam_2 = drill_hole_diam_2

    ########################################################################
    # Alternative Constructors
    ########################################################################

    @classmethod
    def from_beams(
        cls,
        beam,
        other_beam,
        length=None,
        depth_ref_side=None,
        depth_opp_side=None,
        num_drill_hole=0,
        drill_hole_diam_1=20.0,
        drill_hole_diam_2=20.0,
        ref_side_index=0,
    ):
        # type: (Beam, Beam, float, float, float, int, float, float, int) -> SimpleScarf
        print("FROM BEAMS CONSTRUCTOR")
        if num_drill_hole not in [0, 1, 2]:
            raise ValueError("NumDrillHole must be either 0, 1 or 2.")

        depth_ref_side = beam.height / 3.0 if depth_ref_side is None else depth_ref_side
        depth_opp_side = beam.height / 3.0 if depth_opp_side is None else depth_opp_side
        length = beam.height * 3.0 if length is None else length

        orientation = cls._calculate_orientation(beam, other_beam)

        start_x = cls._calculate_start_x(beam, orientation, length)

        return cls(orientation,
                   start_x,
                   length,
                   depth_ref_side,
                   depth_opp_side,
                   num_drill_hole,
                   drill_hole_diam_1,
                   drill_hole_diam_2,
                   ref_side_index=ref_side_index)

    @classmethod
    def from_plane_and_beam(cls, beam, plane):
        print("FROM PLANE AND BEAM CONSTRUCTOR")
        # type: (Beam, Plane) -> SimpleScarf
    
        # Check that the plane is parallel to the beam centerline
        # if abs(plane.normal.dot(beam.centerline.direction)) < 1.0 - TOL.cosine:
        #     raise ValueError("The plane must be parallel to the beam centerline to create a SimpleScarf joint.")

        # Check that the plane intersects with the beam centerline
        # if not plane.intersect_line(beam.centerline):
        #     raise ValueError("The plane must intersect with the beam centerline to create a SimpleScarf joint.")

        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)

        # Check that the plane intersects with the beam centerline at an endpoint
        # intersection = plane.intersect_line(beam.centerline)
        # if not (intersection.is_close(beam.centerline.start) or intersection.is_close(beam.centerline.end)):
        #     raise ValueError("The plane must intersect with the beam centerline at an endpoint to create a SimpleScarf joint.")
        
        orientation = cls._calculate_orientation_with_plane(plane, beam)

        dot = plane.normal.dot(beam.centerline.direction)
        if TOL.is_close(dot, -1.0) or TOL.is_close(dot, 1.0) or TOL.is_close(dot, 0.0):
            ref_side_dict = beam_ref_side_incidence_with_vector(beam, Vector.Zaxis(), ignore_ends=True)
            ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            height_side_index = (ref_side_index + 1) % 4
            vertical_height = beam.ref_edges[ref_side_index].start.distance_to_point(beam.ref_edges[height_side_index].start)
            depth_ref_side = vertical_height / 3.0
            depth_opp_side = vertical_height / 3.0
            length = vertical_height * 3.0
            num_drill_hole = 0
            drill_hole_diam_1 = 20.0
            drill_hole_diam_2 = 20.0

            return cls(orientation,
                       cls._calculate_start_x(beam, orientation, length),
                       length,
                       depth_ref_side,
                       depth_opp_side,
                       num_drill_hole,
                       drill_hole_diam_1,
                       drill_hole_diam_2,
                       ref_side_index=ref_side_index)

        else:
            if dot < 0 and orientation == OrientationType.START or dot > 0 and orientation == OrientationType.END:
                plane.normal = plane.normal * -1
            
            ref_side_dict = beam_ref_side_incidence_with_vector(beam, plane.normal, ignore_ends=True)
            ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            ref_side_angle = min(ref_side_dict.values())
            plane_inclination_angle = abs(ref_side_angle)
            height_side_index = (ref_side_index + 1) % 4
            vertical_height = beam.ref_edges[ref_side_index].start.distance_to_point(beam.ref_edges[height_side_index].start)
            depth_ref_side = vertical_height / 4.0
            depth_opp_side = vertical_height / 4.0
            length = (vertical_height - (depth_ref_side + depth_opp_side)) / math.tan(plane_inclination_angle)
            num_drill_hole = 0
            drill_hole_diam_1 = 20.0
            drill_hole_diam_2 = 20.0
        
            return cls(orientation,
                       cls._calculate_start_x(beam, orientation, length),
                       length,
                       depth_ref_side,
                       depth_opp_side,
                       num_drill_hole,
                       drill_hole_diam_1,
                       drill_hole_diam_2,
                       ref_side_index=ref_side_index)
    
    @classmethod
    def _calculate_orientation_with_plane(cls, plane, beam):
        intersection = plane.intersection_with_line(beam.centerline)
        dis = intersection.distance_to_point(beam.centerline.start)
        die = intersection.distance_to_point(beam.centerline.end)
        if TOL.is_close(dis, 0.0):
            return OrientationType.START
        elif TOL.is_close(die, 0.0):
            return OrientationType.END
        else:
            raise ValueError("The plane must intersect with the beam centerline at an endpoint to create a SimpleScarf joint.")

    @classmethod
    def _calculate_orientation(cls, beam, other_beam):
        ctls_intersection = cls._calculate_average_point(beam, other_beam)
        if not ctls_intersection:
            raise FeatureApplicationError("The beams should share an endpoint to apply a SimpleScarf joint.")
        side, _ = beam.endpoint_closest_to_point(ctls_intersection)
        return OrientationType.START if side == "start" else OrientationType.END

    @staticmethod
    def _calculate_start_x(beam, orientation, length): #TODO: modify to accept bias
        if orientation == OrientationType.START:
            return 0.0
        else:
            return beam.length + length/2

    @staticmethod
    def _calculate_average_point(beam, other_beam):
        dist, p1, p2 = distance_segment_segment_points(beam.centerline, other_beam.centerline)
        p1 = Point(*p1)
        p2 = Point(*p2)
        return (p1 + p2) * 0.5


    #########################################################################
    # Methods
    #########################################################################

    def apply(self, geometry, beam):
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas.geometry.Brep`
            The geometry to be processed.

        beam : :class:`~compas_timber.elements.Beam`
            The beam that is milled by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If?

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing.

        """
        # type: (Brep, Beam) -> Brep
        scarf_volume = self.volume_from_params_and_beam(beam) 
        scarf_volume.transform(beam.transformation_to_local())
        drill_volumes = self.drill_hole_volumes_from_params_and_beam(beam)
        drill_volumes = [dv.transformed(beam.transformation_to_local()) for dv in drill_volumes]

        try:
            scarf_volume = Brep.from_mesh(scarf_volume)
            drill_volumes = [Brep.from_mesh(dv) for dv in drill_volumes]
            json_dump(scarf_volume, "C:/Users/paulj/Downloads/scarf_volume.json")
        except Exception:
            raise FeatureApplicationError(
                scarf_volume,
                geometry,
                "Could not convert the scarf volume mesh to a Brep."
            )

        # Subtract the scarf volume from the beam geometry
        try:
            json_dump(geometry, "C:/Users/paulj/Downloads/sub_geometry.json")
            sub_brep = Brep.from_boolean_difference(geometry, scarf_volume)
            for dv in drill_volumes:
                sub_brep = Brep.from_boolean_difference(sub_brep, dv)
            for b in sub_brep:
                if b.contains(beam.centerline.midpoint.transformed(beam.transformation_to_local())):
                    return b
                
            
            # return actual_b
        except IndexError:
            raise FeatureApplicationError(
                scarf_volume,
                geometry,
                "The scarf volume does not intersect with the beam geometry."
            )

    def _planes_from_params_and_beam(self, beam):
        """Generates the planes needed to define the scarf volume from the feature parameters and the beam.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        list(:class:`~compas.geometry.Plane`)
            The planes of the scarf volume as a list.
        """

        #type: (Beam) -> list[Plane]
        assert self.start_x is not None
        assert self.length is not None
        assert self.depth_ref_side is not None
        assert self.depth_opp_side is not None

        
        ref_surface = beam.side_as_surface(self.ref_side_index)

        top_frame = ref_surface.frame
        if self.orientation == OrientationType.END:
            top_frame.translate(top_frame.xaxis * (beam.length + self.length/2))
        # else:
        #     top_frame.translate(top_frame.xaxis * (self.length/2))
        ref_middle_frame = top_frame.translated(-top_frame.normal * self.depth_ref_side)

        angle_sf = -90 if self.orientation == OrientationType.START else 90
        start_frame = top_frame.rotated(math.radians(angle_sf), top_frame.yaxis, top_frame.point)

        blank_frame = start_frame.translated(start_frame.normal * self.length/2)

        end_frame = start_frame.translated(-start_frame.normal * self.length)

        bottom_frame = beam.opp_side(self.ref_side_index)
        opp_middle_frame = bottom_frame.translated(-bottom_frame.normal * self.depth_opp_side)

        front_frame = beam.front_side(self.ref_side_index)

        back_frame = beam.back_side(self.ref_side_index)

        frames = [top_frame, ref_middle_frame, start_frame, blank_frame, end_frame, opp_middle_frame, bottom_frame, front_frame, back_frame]

        return [Plane.from_frame(frame) for frame in frames]

    def volume_from_params_and_beam(self, beam):
        """Generates a Brep representing the volume to be removed from the beam.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is milled by this instance.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The Brep representing the volume to be removed from the beam.

        """
        # type: (Beam) -> Polyhedron

        top_plane, ref_middle_plane, start_plane, blank_plane, end_plane, opp_middle_plane, bottom_plane, front_plane, back_plane = self._planes_from_params_and_beam(beam)

        vertices = [
            Point(*intersection_plane_plane_plane(top_plane, blank_plane, front_plane)),            #v0
            Point(*intersection_plane_plane_plane(bottom_plane, blank_plane, front_plane)),         #v1
            Point(*intersection_plane_plane_plane(bottom_plane, end_plane, front_plane)),           #v2
            Point(*intersection_plane_plane_plane(opp_middle_plane, end_plane, front_plane)),       #v3
            Point(*intersection_plane_plane_plane(ref_middle_plane, start_plane, front_plane)),     #v4
            Point(*intersection_plane_plane_plane(top_plane, start_plane, front_plane)),            #v5
            Point(*intersection_plane_plane_plane(top_plane, blank_plane, back_plane)),             #v6
            Point(*intersection_plane_plane_plane(top_plane, start_plane, back_plane)),             #v7
            Point(*intersection_plane_plane_plane(ref_middle_plane, start_plane, back_plane)),      #v8
            Point(*intersection_plane_plane_plane(opp_middle_plane, end_plane, back_plane)),        #v9
            Point(*intersection_plane_plane_plane(bottom_plane, end_plane, back_plane)),            #v10
            Point(*intersection_plane_plane_plane(bottom_plane, blank_plane, back_plane)),          #v11
        ]

        faces = [
            [0,1,4,5],          # Front face 1
            [1,2,3,4],          # Front face 2
            [6,7,8,11],         # Back face 1
            [8,9,10,11],        # Back face 2
            [0,5,7,6],          # Top face
            [1,11,10,2],        # Bottom face
            [0,6,11,1],         # Start face
            [9,3,2,10],         # End face
            [4,3,9,8],          # Middle face
            [5,4,8,7]           #  face
        ]
        
        if self.orientation == OrientationType.END:
            faces = [face[::-1] for face in faces]
        return Polyhedron(vertices, faces)
    
    def drill_hole_volumes_from_params_and_beam(self, beam):

        assert self.orientation is not None
        assert self.num_drill_hole is not None
        assert self.drill_hole_diam_1 is not None
        assert self.drill_hole_diam_2 is not None
        assert self.ref_side_index is not None

        ref_surface = beam.side_as_surface(self.ref_side_index)
        ref_frame = ref_surface.frame

        if self.num_drill_hole == 0:
            return []
        
        elif self.num_drill_hole == 1:
            c_radius = self.drill_hole_diam_1 / 2.0
            c_height = max(beam.width, beam.height)
            if self.orientation == OrientationType.START:
                c_frame = Frame(beam.centerline.start, ref_frame.xaxis, ref_frame.yaxis)
            else:
                c_frame = Frame(beam.centerline.end, ref_frame.xaxis, ref_frame.yaxis)
            return [Cylinder(c_radius, c_height, c_frame)]
        
        elif self.num_drill_hole == 2:
            c1_radius = self.drill_hole_diam_1 / 2.0
            c1_height = max(beam.width, beam.height)
            c2_radius = self.drill_hole_diam_2 / 2.0
            c2_height = max(beam.width, beam.height)
            if self.orientation == OrientationType.START:
                c1_frame = Frame(beam.centerline.start.translated(beam.centerline.direction * self.length / 6.0), ref_frame.xaxis, ref_frame.yaxis)
                c2_frame = Frame(beam.centerline.start.translated(beam.centerline.direction * -self.length / 6.0), ref_frame.xaxis, ref_frame.yaxis)
            else:
                c1_frame = Frame(beam.centerline.end.translated(beam.centerline.direction * self.length / 6.0), ref_frame.xaxis, ref_frame.yaxis)
                c2_frame = Frame(beam.centerline.end.translated(beam.centerline.direction * -self.length / 6.0), ref_frame.xaxis, ref_frame.yaxis)
            return [Cylinder(c1_radius, c1_height, c1_frame), Cylinder(c2_radius, c2_height, c2_frame)]

    def scale(self, factor):
        """Scale the parameters of this processing by a given factor.

        Note
        ----
        Only distances are scaled, angles remain unchanged.

        Parameters
        ----------
        factor : float
            The scaling factor. A value of 1.0 means no scaling, while a value of 2.0 means doubling the size.

        """
        self.start_x *= factor
        self.length *= factor
        self.depth_ref_side *= factor
        self.depth_opp_side *= factor
        self.drill_hole_diam_1 *= factor
        self.drill_hole_diam_2 *= factor

class SimpleScarfParams(BTLxProcessingParams):
    """Parameters for the SimpleScarf feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.SimpleScarf`
        The instance of the SimpleScarf feature.
    """

    def __init__(self, instance):
        # type: (SimpleScarf) -> None
        super(SimpleScarfParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the SimpleScarf feature as an ordered dictionary.

        Returns
        -------
        dict
            The parameters of the SimpleScarf as an ordered dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["DepthRefSide"] = "{:.{prec}f}".format(float(self._instance.depth_ref_side), prec=TOL.precision)
        result["DepthOppSide"] = "{:.{prec}f}".format(float(self._instance.depth_opp_side), prec=TOL.precision)
        result["NumDrillHole"] = str(self._instance.num_drill_hole)
        result["DrillHoleDiam1"] = "{:.{prec}f}".format(float(self._instance.drill_hole_diam_1), prec=TOL.precision)
        result["DrillHoleDiam2"] = "{:.{prec}f}".format(float(self._instance.drill_hole_diam_2), prec=TOL.precision)
        return result

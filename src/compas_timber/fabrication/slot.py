import math

from collections import OrderedDict


from compas.geometry import Line
from compas.geometry import Polyline
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Frame
from compas.geometry import Vector
from compas.geometry import Brep
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_segment_plane
from compas.geometry import intersection_line_line

from compas.tolerance import TOL


from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams
from .btlx import OrientationType



from typing import TYPE_CHECKING
from compas_timber.elements.beam import Beam




class Slot(BTLxProcessing):
    PROCESSING_NAME = "Slot"  # type: ignore

    @property
    def __data__(self):
        data = super(Slot, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["angle"] = self.angle
        data["inclination"] = self.inclination
        data["length"] = self.length
        data["depth"] = self.depth
        data["thickness"] = self.thickness
        data["angle_ref_point"] = self.angle_ref_point
        data["angle_opp_point"] = self.angle_opp_point
        data["add_angle_opp_point"] = self.add_angle_opp_point
        data["machining_limits"] = self.machining_limits
        return data

    # fmt: off
    def __init__(
        self,
        orientation=OrientationType.START,
        start_x=0.0,
        start_y=0.0,
        start_depth=0.0,
        angle=90.0,
        inclination=90.0,
        length=200.0,
        depth=10.0,
        thickness=10.0,
        angle_ref_point=90.0,
        angle_opp_point=90.0,
        add_angle_opp_point=0.0,
        machining_limits=None,
        **kwargs
    ):
        super(Slot, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._inclination = None
        self._length = None
        self._depth = None
        self._thickness = None
        self._angle_ref_point = None
        self._angle_opp_point = None
        self._add_angle_opp_point = None
        self._machining_limits = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.inclination = inclination
        self.length = length
        self.depth = depth
        self.thickness = thickness
        self.angle_ref_point = angle_ref_point
        self.angle_opp_point = angle_opp_point
        self.add_angle_opp_point = add_angle_opp_point
        self.machining_limits = machining_limits

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return SlotParams(self)

    @property
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, orientation):
        if orientation not in [OrientationType.START, OrientationType.END]:
            raise ValueError("Orientation must be either OrientationType.START or OrientationType.END. Got: {}".format(orientation))
        self._orientation = orientation

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, start_x):
        if start_x > 100000.0 or start_x < -100000.0:
            raise ValueError("Start X must be between -100000.0 and 100000. Got: {}".format(start_x))
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 50000.0 or start_y < -50000.0:
            raise ValueError("Start Y must be between -50000.0 and 50000.0. Got: {}".format(start_y))
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 50000.0 or start_depth < 0.0:
            raise ValueError("Start Depth must be less than 50000.0 and positive. Got: {}".format(start_depth))
        self._start_depth = start_depth

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle < -90.0 or angle > 90.0:
            raise ValueError("Angle must be between -90.0 and 90.0. Got: {}".format(angle))
        self._angle = angle

    @property
    def inclination(self):
        return self._inclination

    @inclination.setter
    def inclination(self, inclination):
        if inclination > 179.9 or inclination < 0.1:
            raise ValueError("Inclination must be between 0.1 and 179.9. Got: {}".format(inclination))
        self._inclination = inclination

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if length < 0.0 or length > 100000.0:
            raise ValueError("Length must be between 0.0 and 100000.0. Got: {}".format(length))
        self._length = length

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        if depth < 0.0 or depth > 50000.0:
            raise ValueError("Depth must be between 0.0 and 50000.0. Got: {}".format(depth))
        self._depth = depth

    @property
    def thickness(self):
        return self._thickness

    @thickness.setter
    def thickness(self, thickness):
        if thickness < 0.0 or thickness > 50000.0:
            raise ValueError("Thickness must be between 0.0 and 50000.0. Got: {}".format(thickness))
        self._thickness = thickness

    @property
    def angle_ref_point(self):
        return self._angle_ref_point

    @angle_ref_point.setter
    def angle_ref_point(self, angle_ref_point):
        if angle_ref_point < 0.1 or angle_ref_point > 179.9:
            raise ValueError("Angle Ref Point must be between 0.1 and 179.9. Got: {}".format(angle_ref_point))
        self._angle_ref_point = angle_ref_point

    @property
    def angle_opp_point(self):
        return self._angle_opp_point

    @angle_opp_point.setter
    def angle_opp_point(self, angle_opp_point):
        if angle_opp_point < 0.1 or angle_opp_point > 179.9:
            raise ValueError("Angle Opp Point must be between 0.1 and 179.9. Got: {}".format(angle_opp_point))
        self._angle_opp_point = angle_opp_point

    @property
    def add_angle_opp_point(self):
        return self._add_angle_opp_point

    @add_angle_opp_point.setter
    def add_angle_opp_point(self, add_angle_opp_point):
        if add_angle_opp_point < -179.9 or add_angle_opp_point > 179.9:
            raise ValueError("Add Angle Opp Point must be between -179.9 and 179.9. Got: {}".format(add_angle_opp_point))
        self._add_angle_opp_point = add_angle_opp_point

    @property
    def machining_limits(self):
        return self._machining_limits

    @machining_limits.setter
    def machining_limits(self, machining_limits):
        # TODO: figure this one out, a generic class?
        self._machining_limits = machining_limits

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(cls, plane, beam, depth, thickness):
        """Makes a full horizontal or vertical slot accross one of the end faces of the beam.

        Therefore, the provided plane must cut the beam at one of its ends, and it must intersect with exactly two parallel small edges of the side face.
        The length of the slot is equal to the full length accross.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane`
            The plane which specifies the orientation and depth of the Slot.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`~compas_timber.fabrication.Slot`
            The constructed Slot feature.

        """
        # this only really matters if `start_depth` != 0. which we're not dealing with quite yet
        orientation = OrientationType.START

        # angle of rotation is bound to between -90 and 90. the rotation point and axis is determined by start_x and start_y

        # 1. find out of the plane cuts horizontally or vertically
        #   check intersections with the small edges. There should be two intersections with parallel small edges
        #   start_x and start_y are depending on this classification
        # 2. find the angle

        # find relevant end surface
        distance_from_start = distance_point_point(plane.point, beam.centerline.start)
        distance_from_end = distance_point_point(plane.point, beam.centerline.end)
        if distance_from_start < distance_from_end:
            ref_side_index = 4
        else:
            ref_side_index = 5

        ref_side = beam.side_as_surface(ref_side_index)
        # find 2 points of intersection
        # TODO: shove this into some function. what are we? savages?
        small_edge_bottom = Line(ref_side.point_at(0, 0), ref_side.point_at(beam.width, 0))
        small_edge_top = Line(ref_side.point_at(0, beam.height), ref_side.point_at(beam.width, beam.height))
        small_edge_left = Line(ref_side.point_at(0, 0), ref_side.point_at(0, beam.height))
        small_edge_right = Line(ref_side.point_at(beam.width, 0), ref_side.point_at(beam.width, beam.height))

        slot_plane = Plane.from_frame(plane)
        intersection_bottom = intersection_segment_plane(small_edge_bottom, slot_plane)
        intersection_top = intersection_segment_plane(small_edge_top, slot_plane)
        intersection_left = intersection_segment_plane(small_edge_left, slot_plane)
        intersection_right = intersection_segment_plane(small_edge_right, slot_plane)

        # find inclination angle
        # look at the jack rafter cut. but idea might be to cross normal and one of the
        # axes of the ref frame to get the yaw angle between ref_side.xaxis and the horizontal direction of the plane
        yaw_vector = plane.normal.cross(ref_side.yaxis)
        inclination = angle_vectors_signed(yaw_vector, ref_side.xaxis, -ref_side.yaxis, deg=True)

        roll_vector = plane.normal.cross(ref_side.zaxis)
        angle = angle_vectors_signed(ref_side.xaxis, roll_vector, ref_side.zaxis, deg=True)
        print("calculated non-signed angle: {}".format(angle_vectors(ref_side.xaxis, roll_vector, deg=True)))
        print("calculated signed angle: {}".format(angle))

        # adjust 0-360 to -90 to 90
        if angle > 90:
            angle = (180 - angle) * -1
        elif angle < -90:
            angle = (180 + angle) * -1
        print("adjusted angle: {}".format(angle))

        ref_frame = ref_side.frame
        if intersection_bottom and intersection_top:
            length = distance_point_point(intersection_bottom, intersection_top)
            if angle < 0:
                slot_start_point = Point(*intersection_top)
            else:
                slot_start_point = Point(*intersection_bottom)
        elif intersection_left and intersection_right:
            length = distance_point_point(intersection_left, intersection_right)
            slot_start_point = Point(*intersection_left)
        else:
            raise ValueError("The slot plane must fully cross one of the beam's end faces")

        local_intersection = ref_frame.to_local_coordinates(Point(*slot_start_point))
        start_x = local_intersection.x
        start_y = local_intersection.y

        return cls(
            orientation,
            start_x=start_x,
            start_y=start_y,
            angle=angle,
            inclination=inclination,
            length=length,
            depth=depth,
            thickness=thickness,
            ref_side_index=ref_side_index,
        )

    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry: Brep, beam: Beam) -> Brep:
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas.geometry.Brep`
            The beam geometry to be cut.
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If the cutting plane does not intersect with beam geometry.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # get the volume to be removed
        subtraction_volume = self.volume_from_params_and_beam(beam)
        subtraction_volume.transform(beam.transformation_to_local())

        # perform the boolean operation
        cutted_geometry = geometry - subtraction_volume

        return cutted_geometry



    def volume_from_params_and_beam(self, beam: "Beam") -> Brep:
        """
        Calculate the volume of the slot to be removed from the beam based on the slot parameters and the beam geometry.
        
        Parameters
        ----------

        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.

        
        Returns
        -------
        :class:`~compas.geometry.Brep`
            The volume of the slot to be removed from the beam.
            
        """
        # get the reference side of the beam    
        ref_side = beam.side_as_surface(self.ref_side_index)

        # get the origin point and the origin frameof the reference side
        origin_point = ref_side.point_at(0, 0)
        origin_frame = ref_side.frame_at(0, 0)

        # calculates the points of the slot polyline
        p1 = self._find_p1(origin_point, origin_frame)
        slot_frame = self._compute_slot_frame(p1, origin_frame)
        p4 = self._find_p4(p1, slot_frame)
        p3 = self._find_p3(p1, p4, slot_frame)
        p2 = self._find_p2(p1, p3, p4, slot_frame)

        # adjust p1 for a full brep cut (when angles are not perpendiculare it does not fully cut)
        adj_direction_1 = Vector.from_start_end(p4, p1).unitized()
        p1 += adj_direction_1 * (self.start_x + 20)
        adj_direction_2 = Vector.from_start_end(p3, p2).unitized()
        p2 += adj_direction_2 * (self.start_x + 20)

        # build the subtracting volume of the slot
        slot_polyline = Polyline([p1, p2, p3, p4, p1])
        subtracting_volume = Brep.from_extrusion(slot_polyline, slot_frame.zaxis * self.thickness)
        subtracting_volume.translate(slot_frame.zaxis * - (self.thickness / 2))

        return subtracting_volume



    def _find_p1(self, origin_point: Point, origin_frame: Frame) -> Point:
        """
        Computes the position of the point P1 of ths slot (see design2machine pdf for reference).

        Parameters
        ----------
        origin_point : :class:`~compas.geometry.Point`
            The origin point of the reference side of the beam.
        origin_frame : :class:`~compas.geometry.Frame`
            The origin frame of the reference side of the beam.
        
        Returns
        -------
        :class:`~compas.geometry.Point`
            The computed point P1 of the slot.

        """
        p1 = (origin_point
            + origin_frame.xaxis * self.start_x
            + origin_frame.yaxis * self.start_y
            + origin_frame.zaxis * -self.start_depth)
        return p1



    def _find_p2(self, p1: Point, p3: Point, p4: Point, slot_frame: Frame) -> Point:
        """
        Compute the position of the point P2 of ths slot (see design2machine pdf for reference).
        Parameters
        ----------
        p1 : :class:`~compas.geometry.Point`
            The point P1 of the slot.
        p3 : :class:`~compas.geometry.Point`
            The point P3 of the slot.
        p4 : :class:`~compas.geometry.Point`
            The point P4 of the slot.
        slot_frame : :class:`~compas.geometry.Frame`
            The frame aligned with the slot at point p1.
            
        Returns
        -------
        :class:`~compas.geometry.Point`
            The computed point P2 of the slot.

        """

        angle_opp_point_radians = math.radians(self.angle_opp_point)
        add_angle_opp_point_radians = math.radians(self.add_angle_opp_point)

        # find the direction to P2 from P3 with the angle_opp_point and add_angle_opp_point
        vector_to_p2 = Vector.from_start_end(p3, p4)
        angle_of_rotation_to_p2 = angle_opp_point_radians + add_angle_opp_point_radians
        vector_to_p2.rotate(-angle_of_rotation_to_p2, axis = slot_frame.zaxis, point=p3)
        vector_to_p2.unitize()
        # find P2 by projecting P3 to the y axis oxis of the P1 frame with the direction to P2
        p3_p2_line = Line.from_point_and_vector(p3, vector_to_p2)
        yaxis_line = Line.from_point_and_vector(p1, slot_frame.yaxis)
        intersection_point, _ = intersection_line_line(p3_p2_line, yaxis_line)
        p2 = Point(*intersection_point)
        return p2



    def _find_p3(self, p1: Point, p4: Point, slot_frame: Frame) -> Point:
        """
        Compute the position of the point P3 of ths slot (see design2machine pdf for reference).
        
        Parameters
        ----------
        p1 : :class:`~compas.geometry.Point`
            The point P1 of the slot.
        p4 : :class:`~compas.geometry.Point`
            The point P4 of the slot. 
        slot_frame : :class:`~compas.geometry.Frame`
            The frame aligned with the slot at point p1.

        Returns
        -------
        :class:`~compas.geometry.Point`
            The computed point P3 of the slot.

        """
        angle_opp_point_radians = math.radians(self.angle_opp_point)

        # calculate the lineare distan between P4 and P3, can be found with the length value
        distancee_to_p3_from_p4 = self.length / math.sin(angle_opp_point_radians)
        # find the angle in P3 anf build the vector
        vector_to_p3 = Vector.from_start_end(p4, p1)
        angle_of_rotation = math.pi - angle_opp_point_radians
        vector_to_p3.rotate(-angle_of_rotation, axis = slot_frame.zaxis, point=p4)
        vector_to_p3.unitize()
        # create P3
        p3 = (p4 + vector_to_p3 * distancee_to_p3_from_p4)

        return p3
    


    def _find_p4(self, p1: Point, slot_frame: Frame) -> Point:
        """
        Compute the position of the point P4 of ths slot (see design2machine pdf for reference).
        
        Parameters
        ----------
        p1 : :class:`~compas.geometry.Point`
            The point P1 of the slot.
        slot_frame : :class:`~compas.geometry.Frame`
            The frame aligned with the slot at point p1.  

        
        Returns:
        -------
        :class:`~compas.geometry.Point`
            The computed point P4 of the slot.
        """
        angle_ref_point_radians = math.radians(self.angle_ref_point)
        # find P4 by the angle_ref_point in P1 and depth
        distance_to_p4_from_p1  = self.depth / math.sin(angle_ref_point_radians)
        vector_to_p4 = slot_frame.yaxis.rotated(-angle_ref_point_radians, axis=slot_frame.zaxis, point=slot_frame.point).unitized()
        p4 = (p1 + vector_to_p4 * distance_to_p4_from_p1)
        return p4    



    def _compute_slot_frame(self, p1: Point, origin_frame: Frame) -> Frame:
        """ 
        Compute the frame aligned with the slot at point p1.
        This method appy the angle and inclnation paramaters to the frame.

        Parameters
        ----------
        p1 : :class:`~compas.geometry.Point`
            The point where the slot starts, origin of the frame. 
        origin_frame : :class:`~compas.geometry.Frame`
            The reference frame from which the slot frame is derived. Frame base on the reference side of the beam. 

        Returns
        -------
        :class:`~compas.geometry.Frame`
            The computed slot frame at point p1.


        """
        # create and adjust the frame in P1 with
        # the polyline will be created on this frame        
        if self.start_depth == 0:
            slot_frame_untrasformed = Frame(p1, xaxis=-origin_frame.zaxis, yaxis=origin_frame.xaxis)
        else:
            if self.orientation == OrientationType.START:
                slot_frame_untrasformed = Frame(p1, xaxis=origin_frame.xaxis, yaxis=origin_frame.zaxis)
            elif self.orientation == OrientationType.END:
                slot_frame_untrasformed = Frame(p1, xaxis=-origin_frame.xaxis, yaxis=origin_frame.zaxis)
        
       
        # angle and inclination to radians
        angle_radians = math.radians(self.angle)
        inclination_radians = math.radians(self.inclination - 90) # adjusting for this reference frame

        if self.orientation == OrientationType.END:
            angle_radians *= -1
            inclination_radians *= -1   
       
        # set the angle parameter
        slot_frame = slot_frame_untrasformed.rotated(-angle_radians, axis=slot_frame_untrasformed.xaxis, point=p1)
       
        # set the inclination parameter
        slot_frame = slot_frame.rotated(inclination_radians, axis=slot_frame_untrasformed.yaxis, point=p1)
    
        return slot_frame







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
        self.start_y *= factor
        self.start_depth *= factor
        self.length *= factor
        self.depth *= factor
        self.thickness *= factor


class SlotParams(BTLxProcessingParams):
    """A class to store the parameters of a Slot feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.Slot`
        The instance of the Slot feature.

    """

    def __init__(self, instance):
        # type: (Slot) -> None
        super(SlotParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Slot feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Slot feature as a dictionary.
        """
        # type: () -> OrderedDict
        result = OrderedDict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(float(self._instance.start_depth), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
        result["Length"] = "{:.{prec}f}".format(float(self._instance.length), prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(float(self._instance.depth), prec=TOL.precision)
        result["Thickness"] = "{:.{prec}f}".format(float(self._instance.thickness), prec=TOL.precision)
        result["AngleRefPoint"] = "{:.{prec}f}".format(float(self._instance.angle_ref_point), prec=TOL.precision)
        result["AngleOppPoint"] = "{:.{prec}f}".format(float(self._instance.angle_opp_point), prec=TOL.precision)
        result["AddAngleOppPoint"] = "{:.{prec}f}".format(float(self._instance.add_angle_opp_point), prec=TOL.precision)
        result["MachiningLimits"] = {"FaceLimitedStart": "no", "FaceLimitedEnd": "no"}
        return result

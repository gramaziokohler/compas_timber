import math

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Rotation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_point
from compas.geometry import intersection_line_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.elements import FeatureApplicationError

from .btlx_process import BTLxProcess
from .btlx_process import BTLxProcessParams
from .btlx_process import OrientationType
from .btlx_process import TenonShapeType


class DovetailTenon(BTLxProcess):
    """Represents a Dovetail Tenon feature to be made on a beam.

    Parameters
    ----------
    orientation : int
        The orientation of the cut. Must be either OrientationType.START or OrientationType.END.
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. Distance from the beam start to the reference point. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. Distance from the reference edge to the reference point. -5000.0 < start_y < 5000.0.
    start_depth : float
        The start depth of the cut in parametric space of the reference side. Margin on the reference side. -5000.0 < start_depth < 5000.0.
    angle : float
        The angle of the cut. Angle between edge and reference edge. 0.1 < angle < 179.9.
    inclination : float
        The inclination of the cut. Inclination between face and reference side. 0.1 < inclination < 179.9.
    rotation : float
        The rotation of the cut. Angle between axis of the tenon and rederence side. 0.1 < rotation < 179.9.
    length_limited_top : bool
        Whether the top length of the cut is limited. True or False.
    length_limited_bottom : bool
        Whether the bottom length of the cut is limited. True or False.
    length : float
        The length of the cut. 0.0 < length < 5000.0.
    width : float
        The width of the cut. 0.0 < width < 1000.0.
    height : float
        The height of the tenon. 0.0 < height < 1000.0.
    cone_angle : float
        The cone angle of the cut. 0.0 < cone_angle < 30.0.
    use_flank_angle : bool
        Whether the flank angle is used. True or False.
    flank_angle : float
        The flank angle of the cut. Angle of the tool. 5.0 < flank_angle < 35.0.
    shape : str
        The shape of the cut. Must be either 'automatic', 'square', 'round', 'rounded', or 'radius'.
    shape_radius : float
        The radius of the shape of the cut. 0.0 < shape_radius < 1000.0.

    """


    PROCESS_NAME = "DovetailTenon"  # type: ignore

    @property
    def __data__(self):
        data = super(DovetailTenon, self).__data__
        data["orientation"] = self.orientation
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["angle"] = self.angle
        data["inclination"] = self.inclination
        data["rotation"] = self.rotation
        data["length_limited_top"] = self.length_limited_top
        data["length_limited_bottom"] = self.length_limited_bottom
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["cone_angle"] = self.cone_angle
        data["use_flank_angle"] = self.use_flank_angle
        data["flank_angle"] = self.flank_angle
        data["shape"] = self.shape
        data["shape_radius"]
        return data

    def __init__(
        self,
        orientation,
        start_x=0.0,
        start_y=50.0,
        start_depth=50.0,
        angle=95.0,
        inclination=10.0,
        rotation=90.0,
        length_limited_top=True,
        length_limited_bottom=True,
        length=80.0,
        width=40.0,
        height=28.0,
        cone_angle,
        use_flank_angle=False,
        flank_angle=15.0,
        shape=TenonShapeType.AUTOMATIC,
        shape_radius=20.0,
        **kwargs
    ):
        super(DovetailTenon, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._inclination = None
        self._rotation = None
        self._length_limited_top = None
        self._length_limited_bottom = None
        self._length = None
        self._width = None
        self._height = None
        self._cone_angle = None
        self._use_flank_angle = None
        self._flank_angle = None
        self._shape = None
        self._shape_radius = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.inclination = inclination
        self.rotation = rotation
        self.length_limited_top = length_limited_top
        self.length_limited_bottom = length_limited_bottom
        self.length = length
        self.width = width
        self.height = height
        self.cone_angle = cone_angle
        self.use_flank_angle = use_flank_angle
        self.flank_angle = flank_angle
        self.shape = shape
        self.shape_radius = shape_radius

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params_dict(self):
        return StepJointParams(self).as_dict()

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
        if start_x > 100000.0 or start_x < -100000.0:
            raise ValueError("StartX must be between -100000.0 and 100000.")
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 5000.0 or start_y < -5000.0:
            raise ValueError("StartY must be between -5000.0 and 5000.")
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 5000.0 or start_depth < -5000.0:
            raise ValueError("StartDepth must be between -5000.0 and 5000.")
        self._start_depth = start_depth

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle > 179.9 or angle < 0.1:
            raise ValueError("Angle must be between 0.1 and 179.9.")
        self._angle = angle

    @property
    def inclination(self):
        return self._inclination

    @inclination.setter
    def inclination(self, inclination):
        if inclination > 179.9 or inclination < 0.1:
            raise ValueError("Inclination must be between 0.1 and 179.9.")
        self._inclination = inclination

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, rotation):
        if rotation > 179.9 or rotation < 0.1:
            raise ValueError("Rotation must be between 0.1 and 179.9.")
        self._rotation = rotation

    @property
    def length_limited_top(self):
        return self._length_limited_top

    @length_limited_top.setter
    def length_limited_top(self, length_limited_top):
        if not isinstance(length_limited_top, bool):
            raise ValueError("LengthLimitedTop must be either True or False.")
        self._length_limited_top = length_limited_top

    @property
    def length_limited_bottom(self):
        return self._length_limited_bottom

    @length_limited_bottom.setter
    def length_limited_bottom(self, length_limited_bottom):
        if not isinstance(length_limited_bottom, bool):
            raise ValueError("LengthLimitedBottom must be either True or False.")
        self._length_limited_bottom = length_limited_bottom

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if length > 5000.0 or length < 0.0:
            raise ValueError("Length must be between 0.0 and 5000.")
        self._length = length

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width > 1000.0 or width < 0.0:
            raise ValueError("Width must be between 0.0 and 1000.")
        self._width = width

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height):
        if height > 1000.0 or height < 0.0:
            raise ValueError("Height must be between 0.0 and 1000.")
        self._height = height

    @property
    def cone_angle(self):
        return self._cone_angle

    @cone_angle.setter
    def cone_angle(self, cone_angle):
        if cone_angle > 30.0 or cone_angle < 0.0:
            raise ValueError("ConeAngle must be between 0.0 and 30.0.")
        self._cone_angle = cone_angle

    @property
    def use_flank_angle(self):
        return self._use_flank_angle

    @use_flank_angle.setter
    def use_flank_angle(self, use_flank_angle):
        if not isinstance(use_flank_angle, bool):
            raise ValueError("UseFlankAngle must be either True or False.")
        self._use_flank_angle = use_flank_angle

    @property
    def flank_angle(self):
        return self._flank_angle

    @flank_angle.setter
    def flank_angle(self, flank_angle):
        if flank_angle > 35.0 or flank_angle < 5.0:
            raise ValueError("FlankAngle must be between 5.0 and 35.0.")
        self._flank_angle = flank_angle

    @property
    def shape(self):
        return self._shape

    @shape.setter
    def shape(self, shape):
        if shape not in [TenonShapeType.AUTOMATIC, TenonShapeType.SQUARE, TenonShapeType.ROUND, TenonShapeType.ROUNDED, TenonShapeType.RADIUS]:
            raise ValueError("Shape must be either 'automatic', 'square', 'round', 'rounded', or 'radius'.")
        self._shape = shape

    @property
    def shape_radius(self):
        return self._shape_radius

    @shape_radius.setter
    def shape_radius(self, shape_radius):
        if shape_radius > 1000.0 or shape_radius < 0.0:
            raise ValueError("ShapeRadius must be between 0.0 and 1000.")
        self._shape_radius = shape_radius

    @property
    def flange_displacement(self):
        # calculate the flange displacement based on the flange angle and the tenon height
        return self.height / math.tan(math.radians(self.flank_angle))

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_plane_and_beam(cls, plane, beam, step_depth=20.0, heel_depth=0.0, tapered_heel=False, ref_side_index=0):
        """Create a StepJoint instance from a cutting surface and the beam it should cut. This could be the ref_side of the cross beam of a Joint and the main beam.

        Parameters
        ----------
        plane : :class:`~compas.geometry.Plane` or :class:`~compas.geometry.Frame`
            The cutting plane.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.StepJoint`

        """
        # type: (Plane|Frame, Beam, float, float, bool, int) -> StepJoint
        if isinstance(plane, Frame):
            plane = Plane.from_frame(plane)
        plane.normal = plane.normal * -1  # flip the plane normal to point towards the beam
        # define ref_side & ref_edge
        ref_side = beam.ref_sides[ref_side_index]  # TODO: is this arbitrary?
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        # calculate orientation
        orientation = cls._calculate_orientation(ref_side, plane)

        # calculate start_x
        point_start_x = intersection_line_plane(ref_edge, plane)
        if point_start_x is None:
            raise ValueError("Plane does not intersect with beam.")
        start_x = distance_point_point(ref_side.point, point_start_x)

        # calculate strut_inclination
        strut_inclination = cls._calculate_strut_inclination(ref_side, plane, orientation)

        # restrain step_depth & heel_depth to beam's height and the maximum possible heel depth for the beam
        step_depth = beam.height if step_depth > beam.height else step_depth
        max_heel_depth = abs(beam.height / math.tan(math.radians(strut_inclination)))
        heel_depth = max_heel_depth if heel_depth > max_heel_depth else heel_depth

        # define step_shape
        step_shape = cls._define_step_shape(step_depth, heel_depth, tapered_heel)

        return cls(
            orientation, start_x, strut_inclination, step_depth, heel_depth, step_shape, ref_side_index=ref_side_index
        )

    @staticmethod
    def _calculate_orientation(ref_side, cutting_plane):
        # orientation is START if cutting plane normal points towards the start of the beam and END otherwise
        # essentially if the start is being cut or the end
        if is_point_behind_plane(ref_side.point, cutting_plane):
            return OrientationType.END
        else:
            return OrientationType.START

    @staticmethod
    def _bound_length(beam_height, start_depth, length, flange_displacement):
        # bound the inserted lenhgth value to the maximum possible length for the beam
        max_lenght = beam_height - start_depth - flange_displacement
        return length if length < max_lenght else max_lenght

    @staticmethod
    def _bound_width(beam_width, length, width, cone_angle, flange_displacement):
        # bound the inserted width value to the maximum possible width for the beam
        max_width = beam_width - 2*(flange_displacement - length/math.tan(math.radians(cone_angle)))
        return width if width < max_width else max_width

    @staticmethod
    def _define_step_shape(step_depth, heel_depth, tapered_heel):
        # step_shape based on step_depth and heel_depth and tapered_heel variables
        if step_depth > 0.0 and heel_depth == 0.0:
            return StepShape.STEP
        elif step_depth == 0.0 and heel_depth > 0.0:
            if tapered_heel:
                return StepShape.TAPERED_HEEL
            else:
                return StepShape.HEEL
        elif step_depth > 0.0 and heel_depth > 0.0:
            return StepShape.DOUBLE
        else:
            raise ValueError("At least one of step_depth or heel_depth must be greater than 0.0.")

    @staticmethod
    def _calculate_y_displacement_end(beam_height, strut_inclination):
        # Calculates the linear displacement along the y-axis of the ref_side from the origin point to the opposite end of the step.
        displacement_end = beam_height / math.sin(math.radians(strut_inclination))
        return displacement_end

    @staticmethod
    def _calculate_x_displacement_end(beam_height, strut_inclination, orientation):
        # Calculates the linear displacement along the x-axis of the ref_side from the origin point to the opposite end of the step.
        displacement_end = beam_height / math.tan(math.radians(strut_inclination))
        if orientation == OrientationType.END:
            displacement_end = -displacement_end
        return displacement_end

    @staticmethod
    def _calculate_x_displacement_heel(heel_depth, strut_inclination, orientation):
        # Calculates the linear displacement alond the x-axis of the ref_side from the origin point to the heel.
        displacement_heel = heel_depth / (math.sin(math.radians(strut_inclination)))
        if orientation == OrientationType.START:
            displacement_heel = -displacement_heel
        return displacement_heel

    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, beam):
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`compas.geometry.Brep`
            The geometry to be processed.

        beam : :class:`compas_timber.elements.Beam`
            The beam that is milled by this instance.

        Raises
        ------
        :class:`~compas_timber.elements.FeatureApplicationError`
            If the cutting planes do not create a volume that itersects with beam geometry or any step fails.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam) -> Brep

        # get cutting planes from params and beam
        try:
            cutting_planes = self.planes_from_params_and_beam(beam)
        except ValueError as e:
            raise FeatureApplicationError(
                None, geometry, "Failed to generate cutting planes from parameters and beam: {}".format(str(e))
            )

        if self.step_shape == StepShape.STEP:
            for cutting_plane in cutting_planes:
                cutting_plane.normal = cutting_plane.normal * -1
                try:
                    geometry.trim(cutting_plane)
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_plane, geometry, "Failed to trim geometry with cutting planes: {}".format(str(e))
                    )

        elif self.step_shape == StepShape.HEEL:
            trimmed_geometies = []
            for cutting_plane in cutting_planes:
                cutting_plane.normal = cutting_plane.normal * -1
                try:
                    trimmed_geometies.append(geometry.trimmed(cutting_plane))
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_plane, geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
                    )
            try:
                geometry = (
                    trimmed_geometies[0] + trimmed_geometies[1]
                )  # TODO: should be swed (.sew()) for a cleaner Brep
            except Exception as e:
                raise FeatureApplicationError(
                    trimmed_geometies, geometry, "Failed to union trimmed geometries: {}".format(str(e))
                )

        elif self.step_shape == StepShape.TAPERED_HEEL:
            try:
                cutting_plane = cutting_planes[0]
                cutting_plane.normal = cutting_plane.normal * -1
                geometry.trim(cutting_plane)
            except Exception as e:
                raise FeatureApplicationError(
                    cutting_planes, geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
                )

        elif self.step_shape == StepShape.DOUBLE:
            # trim geometry with last cutting plane
            cutting_planes[-1].normal = cutting_planes[-1].normal * -1
            try:
                geometry.trim(cutting_planes[-1])
            except Exception as e:
                raise FeatureApplicationError(
                    cutting_planes[-1], geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
                )
            # trim geometry with first two cutting planes
            trimmed_geometies = []
            for cutting_plane in cutting_planes[:2]:
                cutting_plane.normal = cutting_plane.normal * -1
                try:
                    trimmed_geometies.append(geometry.trimmed(cutting_plane))
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_plane, geometry, "Failed to trim geometry with cutting plane: {}".format(str(e))
                    )
            try:
                geometry = (
                    trimmed_geometies[0] + trimmed_geometies[1]
                )  # TODO: should be swed (.sew()) for a cleaner Brep
            except Exception as e:
                raise FeatureApplicationError(
                    trimmed_geometies, geometry, "Failed to union trimmed geometries: {}".format(str(e))
                )

        if self.tenon and self.step_shape == StepShape.STEP:  # TODO: check if tenon applies only to step in BTLx
            # create tenon volume and subtract from brep
            tenon_volume = self.tenon_volume_from_params_and_beam(beam)
            cutting_planes[0].normal = cutting_planes[0].normal * -1
            # trim tenon volume with cutting plane
            try:
                tenon_volume.trim(cutting_planes[0])
            except Exception as e:
                raise FeatureApplicationError(
                    cutting_planes[0], tenon_volume, "Failed to trim tenon volume with cutting plane: {}".format(str(e))
                )
            # trim tenon volume with second cutting plane if tenon height is greater than step depth
            if self.tenon_height > self.step_depth:
                try:
                    tenon_volume.trim(cutting_planes[1])
                except Exception as e:
                    raise FeatureApplicationError(
                        cutting_planes[1],
                        tenon_volume,
                        "Failed to trim tenon volume with second cutting plane: {}".format(str(e)),
                    )
            # add tenon volume to geometry
            try:
                geometry += tenon_volume
            except Exception as e:
                raise FeatureApplicationError(
                    tenon_volume, geometry, "Failed to add tenon volume to geometry: {}".format(str(e))
                )

        return geometry

    def add_tenon(self, tenon_width, tenon_height):
        """Add a tenon to the existing StepJointNotch instance.

        Parameters
        ----------
        tenon_width : float
            The width of the tenon. tenon_width < 1000.0.
        tenon_height : float
            The height of the tenon. tenon_height < 1000.0.
        """
        self.tenon = True
        # self.tenon_width = beam.width / 4  # TODO: should this relate to the beam? typically 1/3 or 1/4 of beam.width
        self.tenon_width = tenon_width
        self.tenon_height = (
            self.step_depth if tenon_height < self.step_depth else tenon_height
        )  # TODO: should this be constrained?

    def planes_from_params_and_beam(self, beam):
        """Calculates the cutting planes from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Plane`
            The cutting planes.
        """
        assert self.orientation is not None
        assert self.strut_inclination is not None
        assert self.step_shape is not None

        # Get the reference side as a PlanarSurface for the first cut
        ref_side = beam.side_as_surface(self.ref_side_index)
        # Get the opposite side as a PlanarSurface for the second cut and calculate the additional displacement along the xaxis
        opp_side = beam.side_as_surface((self.ref_side_index + 2) % 4)

        # Calculate the displacements for the cutting planes along the y-axis and x-axis
        y_displacement_end = self._calculate_y_displacement_end(beam.height, self.strut_inclination)
        x_displacement_end = self._calculate_x_displacement_end(beam.height, self.strut_inclination, self.orientation)
        x_displacement_heel = self._calculate_x_displacement_heel(
            self.heel_depth, self.strut_inclination, self.orientation
        )

        # Get the points at the start of the step, at the end and at the heel
        p_ref = ref_side.point_at(self.start_x, 0)
        p_opp = opp_side.point_at(self.start_x + x_displacement_end, beam.width)
        p_heel = ref_side.point_at(self.start_x + x_displacement_heel, 0)
        # Create cutting planes at the start of the step, at the end and at the heel
        cutting_plane_ref = Frame(p_ref, ref_side.frame.xaxis, ref_side.frame.yaxis)
        cutting_plane_opp = Frame(p_opp, ref_side.frame.xaxis, ref_side.frame.yaxis)
        cutting_plane_heel = Frame(p_heel, ref_side.frame.xaxis, ref_side.frame.yaxis)

        if self.orientation == OrientationType.START:
            rot_axis = cutting_plane_ref.yaxis
        else:
            rot_axis = -cutting_plane_ref.yaxis

        if self.step_shape == StepShape.STEP:
            return self._calculate_step_planes(cutting_plane_ref, cutting_plane_opp, y_displacement_end, rot_axis)
        elif self.step_shape == StepShape.HEEL:
            return self._calculate_heel_planes(cutting_plane_heel, cutting_plane_opp, rot_axis)
        elif self.step_shape == StepShape.TAPERED_HEEL:
            return self._calculate_heel_tapered_planes(cutting_plane_opp, y_displacement_end, rot_axis)
        elif self.step_shape == StepShape.DOUBLE:
            return self._calculate_double_planes(
                cutting_plane_heel, cutting_plane_opp, y_displacement_end, x_displacement_heel, rot_axis
            )

    def _calculate_step_planes(self, cutting_plane_ref, cutting_plane_opp, displacement_end, rot_axis):
        """Calculate cutting planes for a step."""
        # Rotate cutting plane at opp_side
        angle_opp = math.radians(self.strut_inclination / 2)
        rot_opp = Rotation.from_axis_and_angle(rot_axis, angle_opp, point=cutting_plane_opp.point)
        cutting_plane_opp.transform(rot_opp)

        # Rotate cutting plane at ref_side
        angle_ref = math.radians(self.strut_inclination) + math.atan(
            self.step_depth / (displacement_end - self.step_depth / math.tan(angle_opp))
        )
        rot_ref = Rotation.from_axis_and_angle(rot_axis, angle_ref, point=cutting_plane_ref.point)
        cutting_plane_ref.transform(rot_ref)

        return [Plane.from_frame(cutting_plane_ref), Plane.from_frame(cutting_plane_opp)]

    def _calculate_heel_planes(self, cutting_plane_heel, cutting_plane_opp, rot_axis):
        """Calculate cutting planes for a heel."""
        # Rotate cutting plane at displaced origin
        angle_heel = math.radians(90)
        rot_heel = Rotation.from_axis_and_angle(rot_axis, angle_heel, point=cutting_plane_heel.point)
        cutting_plane_heel.transform(rot_heel)

        # Rotate cutting plane at opp_side
        angle_opp = math.radians(self.strut_inclination)
        rot_opp = Rotation.from_axis_and_angle(rot_axis, angle_opp, point=cutting_plane_opp.point)
        cutting_plane_opp.transform(rot_opp)

        return [Plane.from_frame(cutting_plane_heel), Plane.from_frame(cutting_plane_opp)]

    def _calculate_heel_tapered_planes(self, cutting_plane_opp, displacement_end, rot_axis):
        """Calculate cutting planes for a tapered heel."""
        # Rotate cutting plane at opp_side
        angle_opp = math.radians(self.strut_inclination) - math.atan(
            self.heel_depth
            / (displacement_end - (self.heel_depth / abs(math.tan(math.radians(self.strut_inclination)))))
        )
        rot_opp = Rotation.from_axis_and_angle(rot_axis, angle_opp, point=cutting_plane_opp.point)
        cutting_plane_opp.transform(rot_opp)

        return [Plane.from_frame(cutting_plane_opp)]

    def _calculate_double_planes(
        self, cutting_plane_heel, cutting_plane_opp, displacement_end, displacement_heel, rot_axis
    ):
        """Calculate cutting planes for a double step."""
        # Rotate first cutting plane at displaced origin
        rot_origin = Rotation.from_axis_and_angle(rot_axis, math.radians(90), point=cutting_plane_heel.point)
        cutting_plane_heel.transform(rot_origin)

        # Rotate last cutting plane at opp_side
        rot_opp = Rotation.from_axis_and_angle(
            rot_axis, math.radians(self.strut_inclination / 2), point=cutting_plane_opp.point
        )
        cutting_plane_opp.transform(rot_opp)

        # Translate first cutting plane at heel
        trans_len = math.tan(math.radians(self.strut_inclination)) * displacement_heel
        trans_vect = cutting_plane_heel.xaxis
        cutting_plane_heel_mid = cutting_plane_heel.translated(trans_vect * trans_len)
        # Calculate rotation angle for middle cutting plane
        heel_hypotenus = math.sqrt(math.pow(trans_len, 2) + math.pow(displacement_heel, 2))
        angle_heel = (
            math.radians(self.strut_inclination)
            - math.radians(90)
            + math.atan(
                self.step_depth
                / (
                    displacement_end
                    - heel_hypotenus
                    - self.step_depth / math.tan(math.radians(self.strut_inclination / 2))
                )
            )
        )

        # Rotate middle cutting plane at heel
        rot_heel = Rotation.from_axis_and_angle(rot_axis, angle_heel, point=cutting_plane_heel_mid.point)
        cutting_plane_heel_mid.transform(rot_heel)

        return [
            Plane.from_frame(cutting_plane_heel),
            Plane.from_frame(cutting_plane_heel_mid),
            Plane.from_frame(cutting_plane_opp),
        ]

    def tenon_volume_from_params_and_beam(self, beam):
        """Calculates the tenon volume from the machining parameters in this instance and the given beam

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Returns
        -------
        :class:`compas.geometry.Polyhedron`
            The tenon volume.

        """
        # type: (Beam) -> Mesh

        assert self.tenon
        assert self.tenon_width is not None
        assert self.tenon_height is not None

        # start with a plane aligned with the ref side but shifted to the start of the first cut
        ref_side = beam.side_as_surface(self.ref_side_index)
        opp_side = beam.side_as_surface((self.ref_side_index + 2) % 4)

        x_displacement_end = self._calculate_x_displacement_end(beam.height, self.strut_inclination, self.orientation)

        # Get the points of the top face of the tenon on the ref_side and opp_side
        # x-displcement
        start_x_ref = self.start_x
        start_x_opp = self.start_x + x_displacement_end
        # y-displacement
        start_y = (beam.width - self.tenon_width) / 2
        end_y = start_y + self.tenon_width
        # points at ref_side
        p_ref_start = ref_side.point_at(start_x_ref, start_y)
        p_ref_end = ref_side.point_at(start_x_ref, end_y)
        # points at opp_side
        p_opp_start = opp_side.point_at(start_x_opp, start_y)
        p_opp_end = opp_side.point_at(start_x_opp, end_y)

        # construct the polyline for the top face of the tenon
        tenon_polyline = Polyline([p_ref_start, p_ref_end, p_opp_start, p_opp_end, p_ref_start])

        # calcutate the extrusion vector of the tenon
        extr_vector_length = self.tenon_height / math.sin(math.radians(self.strut_inclination))
        extr_vector = ref_side.frame.xaxis * extr_vector_length
        if self.orientation == OrientationType.START:
            extr_vector = -extr_vector

        # translate the polyline to create the tenon volume
        tenon_polyline_extrusion = tenon_polyline.translated(extr_vector)

        # create Box from tenon points  # TODO: should create Brep directly by extruding the polyline
        tenon_points = tenon_polyline.points + tenon_polyline_extrusion.points
        tenon_box = Box.from_points(tenon_points)

        # convert to Brep and trim with ref_side and opp_side
        tenon_brep = Brep.from_box(tenon_box)
        try:
            tenon_brep.trim(ref_side.to_plane())
            tenon_brep.trim(opp_side.to_plane())
        except Exception as e:
            raise FeatureApplicationError(
                None, tenon_brep, "Failed to trim tenon volume with cutting planes: {}".format(str(e))
            )
        return tenon_brep


class DovetailTenonParams(BTLxProcessParams):
    """A class to store the parameters of a Dovetail Tenon feature.

    Parameters
    ----------
    instance : :class:`~compas_timber._fabrication.DovetailTenon`
        The instance of the Dovetail Tenon feature.
    """

    def __init__(self, instance):
        # type: (DovetailTenon) -> None
        super(DovetailTenonParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Dovetail Tenon feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Dovetail Tenon as a dictionary.
        """
        # type: () -> OrderedDict
        result = super(DovetailTenonParams, self).as_dict()
        result["Orientation"] = self._instance.orientation
        result["StartX"] = "{:.{prec}f}".format(self._instance.start_x, prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(self._instance.start_y, prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(self._instance.start_depth, prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(self._instance.angle, prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(self._instance.inclination, prec=TOL.precision)
        result["Rotation"] = "{:.{prec}f}".format(self._instance.rotation, prec=TOL.precision)
        result["LengthLimitedTop"] = "yes" if self._instance.length_limited_top else "no"
        result["LengthLimitedBottom"] = "yes" if self._instance.length_limited_bottom else "no"
        result["Length"] = "{:.{prec}f}".format(self._instance.length, prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(self._instance.width, prec=TOL.precision)
        result["Height"] = "{:.{prec}f}".format(self._instance.height, prec=TOL.precision)
        result["ConeAngle"] = "{:.{prec}f}".format(self._instance.cone_angle, prec=TOL.precision)
        result["UseFlankAngle"] = "yes" if self._instance.use_flank_angle else "no"
        result["FlankAngle"] = "{:.{prec}f}".format(self._instance.flank_angle, prec=TOL.precision)
        result["Shape"] = self._instance.shape
        result["ShapeRadius"] = "{:.{prec}f}".format(self._instance.shape_radius, prec=TOL.precision)

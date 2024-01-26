from compas.geometry import Surface
from matplotlib.pyplot import box
from numpy import outer
from compas_timber.parts import Beam
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import Frame
from compas.geometry import Polyline
from compas.geometry import offset_polyline
from compas.geometry import angle_vectors
from compas.geometry import bounding_box_xy
from compas.geometry import transform_points
from compas.geometry import matrix_from_frame_to_frame
from compas.geometry import intersection_line_line


def assembly_from_surface(surface, beam_height, beam_width, stud_spacing, z_axis = Vector.Zaxis, sheeting_thickness = None, sheeting_inside = None, lintel_posts = True):
    """Create a timber assembly from a surface.

    Parameters
    ----------
    surface : :class:`compas.geometry.Surface`
        The surface to create the assembly from. must be planar.
    beam_height : float
        The height of the beams aka thickness of wall cavity normal to the surface.
    beam_width : float
        The width of the beams.
    stud_spacing : float
        The spacing between the studs.
    z_axis : :class:`compas.geometry.Vector`, optional
        Determines the orientation of the posts inside the frame.
        Default is ``Vector.Zaxis``.
    sheeting_thickness : :class:`compas.geometry.Surface`, optional
        The thickness of sheeting applied to the assembly. Applies to both sides of assembly unless sheeting_inside is specified.
        Default is ``None``.
    sheeting_inside : :class:`compas.geometry.Surface`, optional
        The inside sheeting thickness of the assembly.
        Default is ``None``.
    lintel_posts : bool, optional
        Add lintel posts to the assembly.
        Default is ``True``.

    Returns
    -------
    :class:`compas_timber.assembly.TimberAssembly`
    """
    if not isinstance(surface, Surface):
        raise TypeError('Expected a compas.geometry.Surface, got: {}'.format(type(surface)))
    if not isinstance(z_axis, Vector):
        raise TypeError('Expected a compas.geometry.Vector, got: {}'.format(type(z_axis)))
    if stud_spacing is not None and not isinstance(stud_spacing, float):
        raise TypeError('Expected a float, got: {}'.format(type(stud_spacing)))
    if sheeting_thickness is not None and not isinstance(sheeting_thickness, float):
        raise TypeError('Expected a float, got: {}'.format(type(sheeting_thickness)))
    if sheeting_inside is not None and not isinstance(sheeting_inside, float):
        raise TypeError('Expected a float, got: {}'.format(type(sheeting_inside)))
    if not isinstance(lintel_posts, bool):
        raise TypeError('Expected a bool, got: {}'.format(type(lintel_posts)))


    surface = surface.faces[0]
    if not surface.is_plane:
        raise ValueError('Surface must be planar.')

    beams = []
    joints = []
    sheeting = []

    edge_polylines = []
    for loop in surface.loops:
        edge_polylines.append(Polyline(loop.vertices))
    edge_polylines.sort(key=lambda pline: pline.length, reverse=True)
    outer_polyline = edge_polylines[0]
    inner_polylines = edge_polylines[1:]

    assembly_frame = Frame(outer_polyline[0], cross_vectors(z_axis, surface.normal), z_axis)
    offset_outer_polyline = offset_polyline(outer_polyline, beam_width/2, normal=surface.normal)
    for line in offset_outer_polyline.lines:
        if angle_vectors(line.direction, z_axis, deg=True) > 45:
            beam = Beam.from_centerline(line, beam_width, beam_height, surface.normal)
            beam.attributes["category"] = "plate"
            beams.append(beam)
        else:
            beam = Beam.from_centerline(line, beam_width, beam_height, surface.normal)
            beam.attributes["category"] = "edge_stud"
            beams.append(beam)

    for polyline in inner_polylines:
        if len(polyline.points) == 5:
            offset_inner_polyline = offset_polyline(polyline, beam_width/2, normal=surface.normal)
            edge_count = 0
            for line in polyline.lines:
                if angle_vectors(line.direction, z_axis, deg=True) > 1:
                    edge_count += 1
                    intersections = intersection_line_line(line, offset_inner_polyline)
                    beam = Beam.from_centerline(line, beam_width, beam_height, surface.normal)
                    beam.attributes["category"] = "king_stud"
                beams.append(beam)


        xform = matrix_from_frame_to_frame(assembly_frame, Frame.worldXY())
        reoriented_points = transform_points(polyline, xform)
        rect = bounding_box_xy(reoriented_points)
        reverse_xform = matrix_from_frame_to_frame(Frame.worldXY(), assembly_frame)
        rect.transform(reverse_xform)







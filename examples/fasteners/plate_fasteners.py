from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import cross_vectors

from compas_timber.connections import TButtJoint
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector
from compas_timber.elements import Beam
from compas_timber.fasteners import Fastener
from compas_timber.fasteners import RectangularPlate
from compas_timber.model import TimberModel
from compas_timber.utils import intersection_line_line_param


def compute_target_frames(cross_beam, main_beam):
    # Find front_face_index and back_face_index
    cross_vector = cross_vectors(cross_beam.centerline.direction, main_beam.centerline.direction)
    cross_faces = beam_ref_side_incidence_with_vector(cross_beam, cross_vector)
    front_face_index = min(cross_faces, key=cross_faces.get)  # type: ignore
    back_face_index = (front_face_index + 2) % 4

    # Compute Front Frame
    (cross_point, cross_param), (main_point, main_param) = intersection_line_line_param(cross_beam.centerline, main_beam.centerline)
    intersection_point = (main_point + cross_point) * 0.05  # type: ignore
    front_face = cross_beam.ref_sides[front_face_index]
    front_point = Plane.from_frame(front_face).closest_point(intersection_point)
    front_frame = Frame(point=front_point, xaxis=cross_beam.centerline.direction, yaxis=front_face.yaxis)

    # Compute Back Frame
    back_face = cross_beam.ref_sides[back_face_index]
    back_point = Plane.from_frame(back_face).closest_point(intersection_point)
    back_frame = Frame(point=back_point, xaxis=-cross_beam.centerline.direction, yaxis=-back_face.yaxis)
    return [front_frame, back_frame]


cross_beam = Beam.from_centerline(Line([0, 0, 0], [2, 0, 0]), width=0.05, height=0.05)
main_beam = Beam.from_centerline(Line([1, 0, 0], [1, 1, 0]), width=0.05, height=0.05)


model = TimberModel()
model.add_elements([cross_beam, main_beam])


# Create a joint with the fastener
joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=0.01, force_pocket=True, conical_tool=True)


plate = RectangularPlate(width=0.05, height=0.025, thickness=0.005, recess=0.005, recess_offset=0.001)
fastener = Fastener()
fastener.add_part(plate)
fastener.target_frames = compute_target_frames(cross_beam, main_beam)


model.add_fastener(fastener, [cross_beam, main_beam])
model.process_joinery()
model.process_fasteners()


for beam in model.beams:
    print(beam)

for fastener in model.fasteners:
    print(fastener)

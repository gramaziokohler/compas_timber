from compas.geometry import angle_vectors


def beam_ref_side_incidence_vector(beam, vector, ignore_ends=True):

    if ignore_ends:
        ref_sides = beam.ref_sides[:4]
    else:
        ref_sides = beam.ref_sides

    ref_side_angles = {}
    for ref_side_index, ref_side in enumerate(ref_sides):
        ref_side_angles[ref_side_index] = angle_vectors(ref_side.normal, vector)

    return ref_side_angles


def beam_ref_side_index(beam, vector):
    ref_side_dict = beam_ref_side_incidence_vector(beam, vector)
    ref_side_index = min(ref_side_dict, key=lambda k: ref_side_dict[k])
    return ref_side_index

# from compas_timber.assembly import TimberAssembly
# #from compas_ghpython import unload_module
# from compas_timber.parts.beam import Beam
# from compas.geometry import Brep as Brep
# from compas.geometry import Frame
# from compas.geometry import Plane
# from compas.geometry import Vector
# import compas.data
# import compas_rhino.geometry

# class BTLx_Part:

#     def __init__(self, brep):
#         strings = self.btlx_part_strings(brep)
#         self.point_string = strings[0]
#         self.indices_string = strings[1]


#     @staticmethod
#     def btlx_part_strings(brep_in):
#         brep = Brep.from_native(brep_in)
#         brep_vertices = brep.vertices
#         brep_vertices_string = ""
#         for vertex in brep_vertices:
#             brep_vertices_string += str(vertex.point.x) + " " + str(vertex.point.y) + " " + str(vertex.point.z) + " "
#         brep_indices = []
#         for face in brep.faces:
#             face_indices = []
#             for edge_index in face.edges():
#                 edge = brep.Edges[edge_index]
#                 start_vertex = edge.StartVertex
#                 end_vertex = edge.EndVertex
#                 face_indices.append(start_vertex.VertexIndex)
#                 face_indices.append(end_vertex.VertexIndex)
#             face_indices = list(set(face_indices))
#             for index in BTLx_Part.ccw_sorted_vertex_indices(face_indices, brep, face):
#                 brep_indices.append(index)
#             brep_indices.append(-1)
#         brep_indices.pop(-1)
#         brep_indices_string = ""
#         for index in brep_indices:
#             brep_indices_string += str(index) + " "
#         return [brep_vertices_string, brep_indices_string]


#     @staticmethod
#     def angle(frame, point):
#         point_vector = Vector(point[0] - frame.point[0], point[1] - frame.point[1], point[2] - frame.point[2])
#         return Vector.angle_vectors_signed(frame.xaxis, point_vector, frame.normal)

#     @staticmethod
#     def ccw_sorted_vertex_indices(indices, brep, brep_face):
#         frame_origin = brep_face.PointAt(0.5, 0.5)
#         frame_normal = brep_face.NormalAt(0.5, 0.5)
#         normal_frame = Frame.from_plane(Plane(frame_origin, frame_normal))
#         sorted_indices = sorted(indices, key=lambda index: BTLx_Part.angle(normal_frame, brep.Vertices[index].Location))
#         return sorted_indices

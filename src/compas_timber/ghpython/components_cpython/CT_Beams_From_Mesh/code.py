# r: compas_timber>=0.15.3
"""Creates a Beam from a LineCurve."""

# flake8: noqa
import Grasshopper
import Rhino
import rhinoscriptsyntax as rs
from compas.geometry import Line
from compas.geometry import Vector
from compas.scene import Scene
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

from compas_timber.elements import Beam
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython


class BeamTreeFromMesh(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, mesh: Rhino.Geometry.Mesh, width: float, height: float, category: str):
        # minimum inputs required
        if not item_input_valid_cpython(ghenv, mesh, "mesh"):
            return
        if not item_input_valid_cpython(ghenv, width, "width"):
            return
        if not item_input_valid_cpython(ghenv, height, "height"):
            return
        edge_index_pairs = []

        points = rs.MeshVertices(mesh)
        faces = rs.MeshFaceVertices(mesh)
        normals = rs.MeshFaceNormals(mesh)

        for face in faces:  # get all the edges of the mesh
            for ind in range(len(face) - 1):
                edge_set = set([face[ind - 1], face[ind]])
                if edge_set not in edge_index_pairs:
                    edge_index_pairs.append(edge_set)

        beam_Zs = []
        for pair in edge_index_pairs:  # get the z direction of the beam using the average of the adjacent face normals
            normal = Vector(0, 0, 0)
            count = 0
            for i, face in enumerate(faces):
                face = set(face)
                if pair.issubset(face):
                    count += 1
                    normal += normals[i]
            beam_Zs.append(normal * (1 / count))

        scene = Scene()
        beam_list = []
        for edge, z in zip(edge_index_pairs, beam_Zs):  # create the beams from the edges
            edge = Line(points[list(edge)[0]], points[list(edge)[1]])
            beam = Beam.from_centerline(edge, width, height, z)
            if category:
                beam.attributes["category"] = category
            beam_list.append(beam)
            scene.add(beam.blank)

        beam_tree = []
        for i in range(len(points)):  # map the beams to the vertices. Each vertex will have a list of beams that are connected to it
            joint_beams = []
            for j, pair in enumerate(edge_index_pairs):
                if i in pair:
                    joint_beams.append(beam_list[j])
            beam_tree.append(joint_beams)

        dt = DataTree[object]()
        for i, beam_branch in enumerate(beam_tree):
            dt.AddRange(beam_branch, GH_Path(i))

        blanks = scene.draw()
        return beam_list, dt, blanks

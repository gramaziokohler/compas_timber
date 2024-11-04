from ghpythonlib.componentbase import executingcomponent as component
import rhinoscriptsyntax as rs
import Grasshopper



class MeshToBeamTree(component):

    def RunScript(self, mesh):

        edge_index_pairs = []

        points = rs.MeshVertices(mesh)
        faces =  rs.MeshFaceVertices(mesh)

        for face in faces:
            for ind in range(len(face)-1):
                edge_set = set([face[ind-1], face[ind]])
                if edge_set not in edge_index_pairs:
                    edge_index_pairs.append(edge_set)

        dt = Grasshopper.DataTree[object]()
        for i in range(len(points)):
            joint_beams = []
            for pair in edge_index_pairs:
                if i in pair:
                    dt.Add(rs.AddLine(points[list(pair)[0]], points[list(pair)[1]]), Grasshopper.Kernel.Data.GH_Path(i))

        return dt


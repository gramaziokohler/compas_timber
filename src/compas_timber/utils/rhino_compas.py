import compas.geometry as cg
import Rhino.Geometry as rg
from compas.datastructures import Mesh


# --------------------------------------------------
# WRAPPERS:
# Rhino.Geometry <> list
def list2rPt(a):
    return rg.Point3d(a[0], a[1], a[2])


def list2rVec(a):
    return rg.Vector3d(a[0], a[1], a[2])


def rVec2list(v):
    return [v.X, v.Y, v.Z]


def rPt2list(p):
    return [p.X, p.Y, p.Z]


def list2rLine(a):
    # tuple or list of two tuples/lists with 3 coordinates each
    return rg.Line(list2rPt(a[0]), list2rPt(a[1]))


# Rhino.Geometry <--> compas.geometry


def cPt2rPt(cPt):
    try:
        return rg.Point3d(cPt.x, cPt.y, cPt.z)
    except:
        return None


def rPt2cPt(rPt):
    try:
        return cg.Point(rPt.X, rPt.Y, rPt.Z)
    except:
        return None


def cVec2rVec(cVec):
    try:
        return rg.Vector3d(cVec.x, cVec.y, cVec.z)
    except:
        return None


def rVec2cVec(rVec):
    try:
        return cg.Vector(rVec.X, rVec.Y, rVec.Z)
    except:
        return None


def cLine2rLine(L):
    try:
        return rg.Line(list2rPt(L[0]), list2rPt(L[1]))
    except:
        return None


def rLine2cLine(L):
    return cg.Line(rPt2cPt(L.PointAt(0.0)), rPt2cPt(L.PointAt(1.0)))


def cPln2rPln(pln):
    try:
        return rg.Plane(list2rPt(pln.point), list2rVec(pln.normal))
    except:
        return None


def cFrame2rPln(cFrame):
    try:
        return rg.Plane(cPt2rPt(cFrame.point), cVec2rVec(cFrame.xaxis), cVec2rVec(cFrame.yaxis))
    except:
        return None


def rPln2cFrame(rPln):
    try:
        return cg.Frame(rPt2cPt(rPln.Origin), rVec2cVec(rPln.XAxis), rVec2cVec(rPln.YAxis))
    except:
        return None


def cBox2rBox(cbox):
    return rg.Box(
        cFrame2rPln(cbox.frame),
        rg.Interval(0, cbox.width),
        rg.Interval(0, cbox.depth),
        rg.Interval(0, cbox.height),
    )


def rMesh2cMesh(rMesh):
    # converts a Rhino.Geometry.Mesh (rMesh) object into a compas.datastructures.Mesh (cMesh) object
    # (uses pieces of code from compas)
    # requires: from compas.datastructures import Mesh

    vertices = rMesh.Vertices
    vertices = [map(float, [vertex.X, vertex.Y, vertex.Z]) for vertex in vertices]
    faces = []
    for F in rMesh.Faces:
        if F.IsTriangle:
            faces.append([F.A, F.B, F.C])
        elif F.IsQuad:
            faces.append([F.A, F.B, F.C, F.D])
        else:
            pass

    faces = [face[:-1] if face[-2] == face[-1] else face for face in faces]
    cMesh = Mesh.from_vertices_and_faces(vertices, faces)
    return cMesh


def cMesh2rMesh(cMesh):
    # converts a compas.datastructures.Mesh (cMesh) object into a Rhino.Geometry.Mesh (rMesh) object
    # (uses pieces of code from compas)

    vertices, faces = cMesh.to_vertices_and_faces()

    disjoint = False  # what is it for?
    rMesh = rg.Mesh()
    if disjoint:
        points = []
        for keys in faces:
            i = len(points)
            facet = [j + i for j in range(len(keys))]
            for key in keys:
                point = vertices[key]
                points.append(point)
                x, y, z = point
                rMesh.Vertices.Add(x, y, z)
            rMesh.Faces.AddFace(*facet)
    else:
        for x, y, z in vertices:
            rMesh.Vertices.Add(x, y, z)
        for face in faces:
            rMesh.Faces.AddFace(*face)
    rMesh.Normals.ComputeNormals()
    rMesh.Unweld(0.01, True)  # makes sharp edges rendered nicely again / splits vertex normals
    rMesh.Compact()
    return rMesh


# other
def rMesh_from8points(pts):
    # explicit constructor of a Rhino.Geometry.Mesh object from 8 points (box). Used in the timber beam projects.
    M = rg.Mesh()
    for pt in pts:
        M.Vertices.Add(pt)

    M.Faces.AddFace(0, 4, 7, 3)
    M.Faces.AddFace(1, 5, 6, 2)
    M.Faces.AddFace(2, 6, 7, 3)
    M.Faces.AddFace(3, 7, 4, 0)
    M.Faces.AddFace(0, 1, 2, 3)
    M.Faces.AddFace(4, 5, 6, 7)
    return M


def brep_from8points(pts):
    B = rg.Brep.CreateFromBox(pts)
    return B


# --------------------------------------------------

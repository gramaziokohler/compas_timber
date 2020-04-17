import Rhino.Geometry as rg
import math


def full_threaded_screw(screw_length=0.300, diameter_shaft=0.006, diameter_thread=0.010, diameter_head=0.012, head_height=0.01):

    # parameters -----------------------------------
    tip_height = head_height*0.5
    thread_length = screw_length-tip_height-head_height
    D1 = diameter_shaft  # 0.006 #inner diameter
    D2 = diameter_thread  # 0.010 #outer/thread diameter
    D3 = diameter_head  # 0.012 #screwhead outer diameter

    # geometry ---------------------------------------
    # shaft
    axis = rg.Line(rg.Point3d(0, 0, head_height), rg.Point3d(0, 0, thread_length+head_height))
    shaft = rg.Brep.CreatePipe(axis.ToNurbsCurve(), D1*0.5, False, 0, False, 1e-6, 1e-3)[0]

    # tip
    #tc1 = rg.Circle(rg.Point3d(0,0,head_height+thread_length), D1*0.5).ToNurbsCurve()
    #tc2 = rg.Ellipse(rg.Plane(rg.Point3d(0,0,L), rg.Vector3d(0,0,1)), D1*0.5*0.5, D1*0.5*0.1).ToNurbsCurve()
    #tip = rg.Brep.CreateFromLoft([tc1,tc2], rg.Point3d.Unset, rg.Point3d.Unset, rg.LoftType.Normal, False)[0]
    tip = rg.Cone(rg.Plane(rg.Point3d(0, 0, screw_length), rg.Vector3d(0, 0, -1)), tip_height, D1*0.5).ToBrep(False)

    # head
    head_pts = [
        rg.Point3d(D1*0.5, 0, head_height),
        rg.Point3d(D1*0.5, 0, head_height*0.8),
        rg.Point3d(D3*0.5, 0, head_height*0.3),
        rg.Point3d(D3*0.5, 0, 0),
        rg.Point3d(0, 0, 0)
    ]
    head_crv = rg.Polyline(head_pts)
    head = rg.RevSurface.Create(head_crv.ToNurbsCurve(), axis).ToBrep()

    solid = rg.Brep.JoinBreps([shaft, head, tip], 1e-5)
    assert len(solid) == 1
    solid = solid[0]

    # thread
    TH = 0.005  # how much it goes up per one turn [m]
    n = 8  # division, points per turn
    k = int(thread_length/TH*8)  # total number of points for the whole thread

    pts1 = [rg.Point3d(math.cos(math.pi*2*((ki % n)/float(n)))*D1*0.5, math.sin(math.pi*2*((ki % n)/float(n)))*D1*0.5, ki*TH/n) for ki in range(k+1)]
    for p in pts1:
        p.Z += head_height
    crv1 = rg.Curve.CreateInterpolatedCurve(pts1, 3)

    pts2 = [rg.Point3d(math.cos(math.pi*2*((ki % n)/float(n)))*D2*0.5, math.sin(math.pi*2*((ki % n)/float(n)))*D2*0.5, ki*TH/n) for ki in range(k+1)]
    for p in pts2:
        p.Z += head_height
    crv2 = rg.Curve.CreateInterpolatedCurve(pts2, 3)

    thread = rg.Brep.CreateFromLoft([crv1, crv2], rg.Point3d.Unset, rg.Point3d.Unset, rg.LoftType.Normal, False)[0]

    # output ---------------------------------------
    screw = [solid, thread]
    return screw


if __name__ == "__main__":
    screw = full_threaded_screw(0.300, 0.006, 0.010, 0.012, 0.010)

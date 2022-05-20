from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.connections.t_butt import TButtJoint, Joint
from compas_timber.parts.beam import Beam
from compas.geometry import Point, Vector



def test_create():
    B1 = Beam.from_endpoints(Point(0, 0.5, 0), Point(1, 0.5, 0), Vector(0, 0, 1), 0.100, 0.200)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(0, 1, 0), Vector(0, 0, 1), 0.100, 0.200)
    A = TimberAssembly()
    A.add_beam(B1)
    A.add_beam(B2)
    J = TButtJoint(A,B1,B2)
    
def test_identical():
        J1 = TButtJoint()
        J2 = TButtJoint()
        J3 = Joint()
        assert J1.is_identical(J3) == False
        assert J1.is_identical(J2) == True
        J1.gap = 0.1
        J2.gap = 0.1
        assert J1.is_identical(J2) == True
        J2.gap = 0.2
        assert J1.is_identical(J2) == False




if __name__ == '__main__':
    test_create()
    test_identical()


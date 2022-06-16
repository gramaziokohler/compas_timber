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
    J = TButtJoint(A, B1, B2)


def test__eq__():

    A1 = TimberAssembly()
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(2, 0, 0), Vector(0, 0, 1), 0.1, 0.2)
    B2 = Beam.from_endpoints(Point(1, 0, 0), Point(1, 1, 0), Vector(0, 0, 1),  0.1, 0.2)
    B3 = Beam.from_endpoints(Point(1, 0, 0), Point(1, 1, 0), Vector(0, 0, 1),  0.1, 0.2)
    B4 = Beam.from_endpoints(Point(1, 0, 0), Point(1, 1, 0), Vector(0, 0, 1),  0.1, 0.4)

    A1.add_beam(B1)
    A1.add_beam(B2)
    A1.add_beam(B3)
    A1.add_beam(B4)


    J1 = TButtJoint(A1,B1,B2)
    try:
        J2 = TButtJoint(A1,B1,B2)
        raise UserWarning('This should not be possible')
    except:
        pass

    # beams look identical but are different beams
    J2 = TButtJoint(A1, B1, B3)
    assert J1 != J2 #TODO: should this fail?

    # beams look different
    J2 = TButtJoint(A1, B1, B4)
    assert J1 != J2


if __name__ == '__main__':
    test_create()
    # test_identical()
    test__eq__()

    print("\n*** all tests passed ***\n\n")

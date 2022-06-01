from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.connections.t_butt import TButtJoint, Joint
from compas_timber.parts.beam import Beam
from compas.geometry import Point, Vector


def test__eq__():

    B1 = Beam.from_endpoints(Point(0,0,0), Point(2,0,0), Vector(0, 0, 1),  0.1, 0.2) 
    B2 = Beam.from_endpoints(Point(1,0,0), Point(1,1,0), Vector(0, 0, 1),  0.1, 0.2)
    B3 = Beam.from_endpoints(Point(1,0,0), Point(1,1,0), Vector(0, 0, 1),  0.1, 0.2) # same as B2
    B4 = Beam.from_endpoints(Point(1,0,0), Point(1,1,0), Vector(0, 0, 1),  0.1, 0.4)
    A = TimberAssembly([B1,B2,B3,B4])
    
    J1 = Joint([B1,B2],A)
    J2 = Joint([B1,B2],A)

    assert J1==J2 # TODO: why is this failing???


if __name__ =='__main__':
    test__eq__()
    print("\n*** all tests passed ***\n\n")
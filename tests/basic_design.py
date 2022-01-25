from compas_timber.assembly.assembly2 import TimberAssembly
from compas_timber.parts.beam2 import Beam
from compas.geometry import Point, Vector

def create_beam(): 
    B = Beam.from_endpoints(Point(0,0,0),Point(0,1,0),Vector(0,0,1),0.100,0.200)
    print(B)
    pass

def create_assembly():
    A = TimberAssembly()
    print(A)
    pass

def mini_design():
    B1 = Beam.from_endpoints(Point(0,0,0),Point(0,1,0),Vector(0,0,1),0.100,0.200)
    B2 = Beam.from_endpoints(Point(0,0.5,0),Point(1,0.5,0),Vector(0,0,1),0.100,0.200)

    A = TimberAssembly()
    A.add_beam(B1)
    A.add_beam(B2)
    print(A._beams)

if __name__=="__main__":
    mini_design()


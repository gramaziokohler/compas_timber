from compas.geometry.shapes import Cylinder
from compas.geometry import Circle, Plane, Point, Vector
from pprint import pprint


class RoundHole(object):
    def __init__(self, endpoint, ray, radius, part=None):
        """
        Defines a shape of a cylindrical recess, hole, through-hole etc., to drill or mill.

        endpoint: To make a through-hole, the endpoint must be outside of the material and the ray must interesect it twice
        ray: vector defining the centreline/axis of the hole, pointing the opposite direction as the direction from which the drill would enter the material. 
            Per default the length will be taken as the height of the cylinder.
        radius: radius of the hole (>= radius of the drillbit)
        part: part into drill into

        """
        self.endpoint = endpoint
        self.axis = ray
        self.radius = radius
        self.part = part
        self.cap_type = 'flat'  # later add round cap, conical cap


    def __repr__(self):
        return 'RoundHole({0!r}, {1!r}, Radius={2!r})'.format(self.endpoint, self.axis, self.radius)

    @property
    def auto_height(self):
        # determine the height of the cylinder from intersections with the part
        NotImplementedError

    def shape(self, autoheight=False):
        # create a cylinder shape as a negative booleand shape to subtract from the part
        circle = Circle(Plane(self.endpoint, self.axis), self.radius)
        if autoheight:
            height = self.auto_height()
        else:
            height = self.axis.length
        return Cylinder(circle, height)


if __name__ == '__main__':

    p = Point(1, 2, 3)
    v = Vector(0, 0, 4.56)
    r = 0.789
    hole = RoundHole(p, v, r)
    print(hole)
    pprint(hole.shape())

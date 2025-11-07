import abc

from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_timber.elements import PlateGeometry

class SlabFeature(abc.ABC):
    """Abstract base class for slab features."""


class SlabOpening(SlabFeature, PlateGeometry):
    """Class representing an opening in a slab."""

    def __init__(self, position_x, position_y, length, width, thickness, local_outline_a=None, local_outline_b=None, name=None, **kwargs):
        local_outline_a = local_outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        local_outline_b = local_outline_b or Polyline([Point(p[0], p[1], thickness) for p in local_outline_a.points])
        PlateGeometry.__init__(self, local_outline_a, local_outline_b, **kwargs)
        self.length = length
        self.width = width
        self.position_x = position_x
        self.position_y = position_y

    @classmethod
    def from_polyline_slab(cls, polyline, slab):
        """Create a SlabOpening from a polyline and slab geometry.

        Parameters
        ----------
        polyline : compas.geometry.Polyline
            The polyline defining the opening.
        slab : compas_timber.elements.PlateGeometry
            The slab geometry.

        Returns
        -------
        SlabOpening
            An instance of SlabOpening.
        """
        polyline = polyline.transformed(slab.modeltransformation.inverse())
        return cls.from_outline_thickness(polyline, slab.thickness, vector=slab.normal)

    @classmethod
    def from_outlines(cls, outline_a, outline_b, **kwargs):

        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b)
        PlateGeometry._check_outlines(args["local_outline_a"], args["local_outline_b"])
        return cls(position_x=args["frame"].point.x, position_y=args["frame"].point.y, length=args["box"].xsize, width=args["box"].ysize, thickness=args["box"].zsize, local_outline_a=args["local_outline_a"], local_outline_b=args["local_outline_b"], **kwargs)
    


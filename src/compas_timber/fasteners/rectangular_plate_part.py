from __future__ import annotations

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Transformation

from compas_timber.fabrication import Drilling
from compas_timber.fabrication import Pocket

from .plate_hole import PlateHole
from .utilities import beam_ref_side_index


class RectangularPlate:
    """
    Describes a rectangular plate that can be used as part of a fastener.

    It has a width, height, thickness, and can have holes.
    The plate can create a recess (Pocket Feature) int he the beam.

    Parameters
    ----------
    width : float
        The width of the plate (xaxis of the reference frame).
    height : float
        The height of the plate (yaxis of the reference frame).
    thickness : float
        The thickness of the plate (zaxis of the reference frame).
    frame : Frame, optional
        The frame of the plate, by default Frame.worldXY().
    recess : float, optional
        The depth of the recess to be milled in the beam, by default 0 (no recess).
    recess_offset : float, optional
        The offset of the recess from the plate dimensions, by default 0 (recess has the same dimensions as the plate).

    Attributes
    ----------
    width : float
        The width of the plate (xaxis of the reference frame).
    height : float
        The height of the plate (yaxis of the reference frame).
    thickness : float
        The thickness of the plate (zaxis of the reference frame).
    holes : list[PlateHole]
        The holes in the plate.
    frame : Frame
        The frame of the plate.
    recess : float
        The depth of the recess to be milled in the beam.
    recess_offset : float
        The offset of the recess from the plate dimensions.
    geometry : Brep
        The geometry of the plate with holes as a Brep.
     blank_geometry : Polyhedron
        The geometry of the plate without holes as a Polyhedron.

    """

    def __init__(self, width: float, height: float, thickeness: float, frame: Frame = Frame.worldXY(), recess: float = 0, recess_offset: float = 0):
        self.width = width
        self.height = height
        self.thickness = thickeness
        self.holes = []
        self.frame = frame
        self.recess = recess
        self.recess_offset = recess_offset

    def copy(self) -> RectangularPlate:
        new_plate = RectangularPlate(self.width, self.height, self.thickness, self.frame.copy())
        new_plate.recess = self.recess
        new_plate.recess_offset = self.recess_offset
        new_plate.holes = [hole.copy() for hole in self.holes]
        return new_plate

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, value):
        if not isinstance(value, Frame):
            raise ValueError("frame should be a Frame object.")
        for hole in self.holes:
            hole.frame.transform(Transformation.from_frame_to_frame(self._frame, value))
        self._frame = value

    @property
    def geometry(self):
        box = self.blank_geometry
        box_brep = Brep.from_mesh(box.to_mesh())
        for hole in self.holes:
            box_brep -= hole.geometry
        if self.recess > 0:
            box_brep.translate(self.frame.zaxis * -self.recess)
        return box_brep

    @property
    def blank_geometry(self):
        box = Box(self.width, self.height, self.thickness, frame=self.frame)
        box.frame.point += self.frame.zaxis * self.thickness / 2
        box = box.to_polyhedron()
        return box

    def add_hole_point_diameter(self, point: Point, diameter: float, apply_drilling=True, drilling_depth=5, drilling_diameter=2) -> PlateHole:
        """
        Add a hole by sepcifing the point and the diameter of the hole.

        Parameters
        ----------
        point : Point
            The point where the hole should be added, relative to the plate frame.
        diameter : float
            The diameter of the hole.
        apply_drilling : bool, optional
            Whether to apply drilling for this hole, by default True.
        drilling_depth : float, optional
            The depth of the drilling, by default 5.
        drilling_diameter : float, optional
            The diameter of the drilling, by default 2.

        Returns
        -------
        PlateHole
            The created PlateHole object.

        """
        hole_frame = self.frame.copy()
        hole_frame.point = point
        hole = PlateHole(hole_frame, diameter, self.thickness, apply_drilling=apply_drilling, drilling_depth=drilling_depth, drilling_diameter=drilling_diameter)
        self.add_hole(hole)
        return hole

    def add_hole(self, hole: PlateHole):
        """
        Add a hole to the plate.

        Parameters
        ----------
        hole : PlateHole
            The hole to be added to the plate.
        """
        self.holes.append(hole)

    def add_hole_grid(self, nx: int, ny: int, border_padding: float, diameter: float, apply_drilling=True, drilling_depth=5, drilling_diameter=2) -> list[PlateHole]:
        """
        Add a grid of holes to the plate.

        Parameters
        ----------
        nx : int
            The number of holes in the x direction.
        ny : int
            The number of holes in the y direction.
        border_padding : float
            The padding from the border of the plate to the first and last holes.
        diameter : float
            The diameter of the holes.

        Returns
        -------
        list[PlateHole]
            The created PlateHole objects.
        """
        holes = []
        for ix in range(nx):
            for iy in range(ny):
                x = self.frame.point.x + border_padding + ix * (self.width - 2 * border_padding) / (nx - 1)
                x -= self.width / 2

                y = self.frame.point.y + border_padding + iy * (self.height - 2 * border_padding) / (ny - 1)
                y -= self.height / 2

                hole = self.add_hole_point_diameter(Point(x, y, 0), diameter, apply_drilling, drilling_depth, drilling_diameter)
                holes.append(hole)
        return holes

    def apply_features(self, elements):
        """
        Apply the features of the plate to the given elements.
        This includes creating pockets for the recess and drillings for the holes.

        Parameters
        ----------
        elements : list[Element]
            The elements to which the features of the plate should be applied.
        """
        for element in elements:
            ref_side_index = beam_ref_side_index(element, self.frame.zaxis)

            # recess Pocket
            geo = self._compute_recess_milling_volume()
            if geo:
                pocket = Pocket.from_volume_and_element(geo, element, ref_side_index=ref_side_index)
                element.add_feature(pocket)

            # # Drillings
            for hole in self.holes:
                if not hole.apply_drilling:
                    continue
                drill_line = hole.drilling_line
                drill_line.start += self.frame.zaxis * self.thickness
                drill_line.end += self.frame.zaxis * -(self.thickness + self.recess)
                try:
                    drilling = Drilling.from_line_and_element(drill_line, element, hole.drilling_diameter)
                    element.add_feature(drilling)
                except Exception:
                    pass

    def _compute_recess_milling_volume(self):
        if self.recess <= 0:
            return None
        recess_box = Box(xsize=(self.width + self.recess_offset * 2), ysize=(self.height + self.recess_offset * 2), zsize=self.recess, frame=self.frame)
        recess_box.frame.point.translate(-self.frame.zaxis * (self.recess / 2))
        return recess_box.to_polyhedron()

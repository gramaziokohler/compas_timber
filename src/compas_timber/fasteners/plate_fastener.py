from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Polyline
from compas.tolerance import Tolerance

from compas_timber.fasteners.fastener import Fastener
from compas_timber.fasteners.hole_interface import HoleInterface  # noqa F401
from compas_timber.fasteners.interface import Interface
from compas_timber.fasteners.recess_interface import RecessInterface  # noqa F401

if TYPE_CHECKING:
    pass

TOL = Tolerance()


class PlateFastener2(Fastener):
    def __init__(self, frame: Frame, outline: Polyline, thickness: float, interfaces: Optional[list[Interface]] = None, **kwargs):
        super().__init__(frame=frame, interfaces=interfaces, **kwargs)
        self.outline = outline
        self.thickness = thickness

    @property
    def __data__(self):
        data = {"frame": self.frame.__data__, "outline": self.outline.__data__, "thickness": self.thickness, "interfaces": [interface.__data__ for interface in self.interfaces]}
        return data

    @classmethod
    def __from_data__(cls, data):
        fastener = cls(
            frame=Frame(data["frame"]["point"], data["frame"]["xaxis"], data["frame"]["yaxis"]),
            outline=Polyline.__from_data__(data["outline"]),  # type: ignore
            thickness=data["thickness"],
        )

        interfaces = [globals()[iface["type"]].__from_data__(iface) for iface in data.get("interfaces", [])]

        for interface in interfaces:
            fastener.add_interface(interface)
        return fastener

    def compute_elementgeometry(self, include_interfaces=True) -> Brep:
        """
        Compute the geometry of the element in local coordinates.

        Parameters
        ----------
        include_interfaces : bool, optional
            If True, the interfaces are applied to the creation of the geometry. Default is True.

        Returns
        -------
        :class:`compas.geometry.Brep`
        """
        # Compute basis geometry
        extrusion = self.frame.zaxis * self.thickness
        geometry = Brep.from_extrusion(self.outline, extrusion)

        # Modify it with the interfaces
        if self.interfaces and include_interfaces:
            for interface in self.interfaces:
                geometry = interface.apply_to_fastener_geometry(geometry)

        geometry.transform(self.to_joint_transformation)

        return geometry

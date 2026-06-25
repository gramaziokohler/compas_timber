from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Optional

from compas_timber.planning import BuildingPlan

if TYPE_CHECKING:
    pass


class BuildingPlanModelContainer:
    """Container for a BuildingPlan and the design elements it references.

    Parameters
    ----------
    plan : BuildingPlan
        The building plan.
    elements : dict, optional
        A dictionary of design elements referenced by the plan. Map element GUIDs to elements.
    geometries : dict, optional
        A dictionary of geometries associated with the design elements. Map element GUIDs to geometries.
    """

    def __init__(self, plan: BuildingPlan, elements: Optional[Dict[str, Any]] = None, geometries: Optional[Dict[str, Any]] = None):
        self.plan = plan
        self.elements = elements or {}
        self.geometries = geometries or {}

    def add_element(self, element: Any, geometry: Any):
        """Add a design element and its associated geometry to the container.

        Parameters
        ----------
        element : Element or Beam
            The design element to add.
        geometry : Mesh, Box, Cylinder, Sphere, or str
            The geometry associated with the design element. If str, it's a filepath to an OBJ file.
        """
        self.elements[str(element.guid)] = element
        self.geometries[str(element.guid)] = geometry

import math
import random
from abc import ABC
from abc import abstractmethod
from warnings import warn

from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polygon
from compas.geometry import Polyline
from compas.geometry import Rotation
from compas.geometry import Transformation
from compas.geometry import Translation
from compas.geometry import Vector
from compas.geometry import is_polygon_in_polygon_xy
from compas.tolerance import TOL


class NestedElementData(Data):
    """
    Data container for elements nested within stock pieces.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The position frame of the element within the stock.
    key : str, optional
        A human-readable identifier for the element.
    length : float, optional
        The length of the element (for beams).

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The position frame of the element within the stock.
    key : str or None
        A human-readable identifier for the element.
    length : float or None
        The length of the element (for beams), None if not applicable.
    """

    def __init__(self, frame, key=None, length=None):
        super(NestedElementData, self).__init__()
        self.frame = frame
        self.key = key
        self.length = length

    @property
    def __data__(self):
        return {
            "frame": self.frame,
            "key": self.key,
            "length": self.length,
        }


class Stock(Data, ABC):
    """
    A base class to represent a stock piece for nesting.

    Parameters
    ----------
    length : float
        Length of the stock piece.
    width : float
        Width of the stock piece.
    height : float
        Height of the stock piece.
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, :class:`NestedElementData`], optional
        Dictionary mapping element GUID (str) to nested element data.


    Attributes
    ----------
    length : float
        Length of the stock piece.
    width : float
        Width of the stock piece.
    height : float
        Height of the stock piece.
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, :class:`NestedElementData`]
        Dictionary mapping element GUID (str) to nested element data.
    """

    def __init__(self, length, width, height, spacing=0.0, element_data=None):
        super(Stock, self).__init__()
        self.length = length
        self.width = width
        self.height = height
        self.spacing = spacing
        self.element_data = element_data or {}

    @property
    def __data__(self):
        return {
            "spacing": self.spacing,
            "element_data": self.element_data,
        }

    @abstractmethod
    def add_element(self, element):
        """
        Add an element to this stock assignment.

        Parameters
        ----------
        element : :class:`~compas_timber.elements.Element`
            The element to add.

        Raises
        ------
        ValueError
            If element doesn't fit in remaining space.
        """
        pass

    @abstractmethod
    def can_fit_element(self, element):
        """
        Check if an element can fit in the remaining space.

        Parameters
        ----------
        element : :class:`~compas_timber.elements.Element`
            The element to check

        Returns
        -------
        bool
            True if element fits in remaining space, False otherwise
        """
        pass

    @abstractmethod
    def is_compatible_with(self, element):
        """
        Check if this stock can accommodate the element type and dimensions.

        Parameters
        ----------
        element : :class:`~compas_timber.elements.Element`
            The element to check

        Returns
        -------
        bool
            True if element is compatible with this stock, False otherwise
        """
        pass


class BeamStock(Stock):
    """
    A class to represent a stock piece for nesting beams.

    Similar to a Beam but represents raw material stock that can have beams assigned to it.

    Parameters
    ----------
    length : float
        Length of the stock piece.
    cross_section : tuple of float
        Cross-section dimensions (width, height).
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, :class:`NestedElementData`], optional
        Dictionary mapping element GUID (str) to nested element data.


    Attributes
    ----------
    length : float
        Length of the stock piece.
    cross_section : tuple of float
        Cross-section dimensions sorted in ascending order for consistent comparison.
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, :class:`NestedElementData`]
        Dictionary mapping element GUID (str) to nested element data.
    """

    def __init__(self, length, cross_section, spacing=0.0, element_data=None):
        # Validate cross_section before passing to parent constructor
        if not isinstance(cross_section, (list, tuple)) or len(cross_section) != 2:
            raise ValueError("cross_section must be a tuple or list of 2 dimensions")
        super(BeamStock, self).__init__(length=length, width=cross_section[0], height=cross_section[1], spacing=spacing, element_data=element_data)
        self.cross_section = tuple(cross_section)
        self._current_x_position = 0.0  # Track current position along length for placing beams

    @property
    def __data__(self):
        data = super(BeamStock, self).__data__
        data["cross_section"] = self.cross_section
        data["length"] = self.length
        return data

    @property
    def _remaining_length(self):
        # Get remaining unused length of the stock piece.
        return self.length - self._current_x_position

    def can_fit_element(self, beam):
        """
        Check if a beam can fit in the remaining space.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to check

        Returns
        -------
        bool
            True if beam fits in remaining length, False otherwise
        """
        return self._remaining_length >= beam.blank_length

    def is_compatible_with(self, beam):
        """
        Check if this stock can accommodate the beam type and dimensions.

        For 1D nesting, we only optimize along the length dimension.
        The cross-sections must be identical.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to check

        Returns
        -------
        bool
            True if beam is compatible with this stock, False otherwise
        """
        # Use a tolerance-based comparison for cross-section dimensions, regardless of order.
        # Compare as sets, but with tolerance: both must have the same two values, order-insensitive.
        a, b = sorted(self.cross_section)
        x, y = sorted([beam.width, beam.height])
        return TOL.is_close(a, x) and TOL.is_close(b, y)

    def add_element(self, beam):
        """
        Add a beam to this stock assignment.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to add

        Raises
        ------
        ValueError
            If beam doesn't fit in remaining space
        """
        if not self.can_fit_element(beam):
            warn(f"Beam with length {beam.blank_length} doesn't fit in remaining space {self._remaining_length}")
            return
        # Get position frame based on orientation
        position_frame = self._get_position_frame(beam)
        self._current_x_position += beam.blank_length + self.spacing  # Update position for next beam
        # Store element data using NestedElementData type
        self.element_data[str(beam.guid)] = NestedElementData(
            frame=position_frame,
            key=beam.name + "-" + str(beam.guid)[:4],
            length=beam.blank_length,
        )

    def _get_position_frame(self, beam):
        # Get the position frame for a beam that is being added to this stock.
        # Orientation is based on the beam's cross-section relative to the stock's.
        beam_cross_section = tuple([beam.width, beam.height])
        # scenario where beam cross-section matches stock exactly (same width and height, same orientation)
        if beam_cross_section == self.cross_section:
            position_frame = Frame.worldXY()
        # scenario where beam cross-section values are the same but orientation is rotated 90 degrees
        else:
            position_frame = Frame([0, 0, 0], [1, 0, 0], [0, 0, 1])
            position_frame.point.y = self.cross_section[1]  # offset in Y by stock height
        position_frame.point.x = self._current_x_position
        return position_frame


class PlateStock(Stock):
    """
    A class to represent a stock piece for nesting plates.

    Similar to a Plate but represents raw material stock that can have plates assigned to it.

    Parameters
    ----------
    dimensions: tuple of float
        Dimensions of the stock piece (length, width).
    thickness : float
        Thickness of the stock piece.
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, :class:`NestedElementData`], optional
        Dictionary mapping element GUID (str) to nested element data.


    Attributes
    ----------
    dimensions : tuple of float
        Dimensions of the stock piece (length, width).
    thickness : float
        Thickness of the stock piece
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, :class:`NestedElementData`]
        Dictionary mapping element GUID (str) to nested element data.

    """

    def __init__(self, dimensions, thickness, spacing=0.0, element_data=None):
        # Validate dimensions before passing to parent constructor
        if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 2:
            raise ValueError("dimensions must be a tuple or list of 2 dimensions")
        super(PlateStock, self).__init__(length=dimensions[0], width=dimensions[1], height=thickness, spacing=spacing, element_data=element_data)
        self.dimensions = tuple(dimensions)
        self.thickness = thickness

        # Initialize remaining boundary as full stock rectangle
        self._remaining_boundary = Polygon([Point(0, 0, 0), Point(dimensions[0], 0, 0), Point(dimensions[0], dimensions[1], 0), Point(0, dimensions[1], 0)])
        self._skyline = Polyline([[0, 0, 0], [self.dimensions[0], 0, 0]])  # setup skyline for nesting algorithms
        self.placement_data = {}  # {guid: Frame} raw XY placement frames for visualization/debug
        self._used_area = 0.0  # explicit area accounting for robust utilization reporting
        self._used_max_x = 0.0  # tracked used envelope extent along X for skyline scoring
        self._used_max_y = 0.0  # tracked used envelope extent along Y for skyline scoring

    @property
    def __data__(self):
        data = super(PlateStock, self).__data__
        data["dimensions"] = self.dimensions
        data["thickness"] = self.thickness
        return data

    @property
    def _remaining_area(self):
        # Get remaining available area in the stock.
        if isinstance(self._remaining_boundary, Polygon):
            return self._remaining_boundary.area
        # Defensive fallback if boundary got corrupted by a failed boolean op.
        return self.dimensions[0] * self.dimensions[1]

    def is_compatible_with(self, plate):
        """
        Check if this stock can accommodate the plate type and dimensions.

        For 2D nesting, plates must have matching thickness.
        The plate's 2D outline must fit within the stock dimensions.

        Parameters
        ----------
        plate : :class:`~compas_timber.elements.Plate`
            The plate to check

        Returns
        -------
        bool
            True if plate is compatible with this stock, False otherwise
        """
        return TOL.is_close(plate.thickness, self.thickness)

    def can_fit_element(self, plate_outline):
        """
        Check if a plate can fit in the remaining space.

        Two-step optimization check:
        1. Area check - fast rejection based on area comparison
        2. Shape check - validate if plate's polygon can fit within remaining boundary

        Parameters
        ----------
        plate_outline : :class:`compas.geometry.Polygon`
            The polygon to check

        Returns
        -------
        bool
            True if plate could fit somewhere in remaining space, False otherwise
        """
        # TODO (acknowledged): API mismatch with abstract Stock.can_fit_element(element).
        # Plate nesting operates on pre-transformed footprint polygons for performance.
        # Keep this behavior for backward compatibility; revisit in a future API revision.

        # Step 1: Quick area rejection
        if plate_outline.area > self._remaining_area:
            return False
        # Step 2: Shape check.
        # NOTE: `is_polygon_in_polygon_xy` can be strict for boundary-touching cases.
        # In nesting we generally allow touching stock boundaries.
        if isinstance(self._remaining_boundary, Polygon) and is_polygon_in_polygon_xy(plate_outline, self._remaining_boundary):
            return True

        # Fallback: allow boundary-touching placements using a tolerant bbox test.
        # This keeps placements robust in Rhino/COMPAS numerical edge cases.
        if isinstance(self._remaining_boundary, Polygon):
            boundary_points = self._remaining_boundary.points
        else:
            # Defensive fallback to stock extents if boundary got corrupted.
            boundary_points = [
                Point(0, 0, 0),
                Point(self.dimensions[0], 0, 0),
                Point(self.dimensions[0], self.dimensions[1], 0),
                Point(0, self.dimensions[1], 0),
            ]
        min_x = min(p.x for p in boundary_points) - TOL.absolute
        max_x = max(p.x for p in boundary_points) + TOL.absolute
        min_y = min(p.y for p in boundary_points) - TOL.absolute
        max_y = max(p.y for p in boundary_points) + TOL.absolute

        return all(min_x <= p.x <= max_x and min_y <= p.y <= max_y for p in plate_outline.points)

    def add_element(self, plate, transformation=Transformation()):
        """
        Add a plate to this stock assignment at a specific position and rotation.

        This updates the remaining boundary by subtracting the placed plate polygon.

        Parameters
        ----------
        plate : :class:`~compas_timber.elements.Plate`
            The plate to add
        transformation : :class:`compas.geometry.Transformation`, optional
            Transformation defining position and rotation of the plate within the stock.

        Raises
        ------
        ValueError
            If plate doesn't fit in remaining space
        """
        # Raw placement frame in XY nesting coordinates.
        placement_frame = Frame.from_transformation(transformation)

        # Transform current local outline to placement position.
        plate_outline = plate.plate_geometry.outline_a.transformed(transformation)

        # Convert Polyline -> Polygon for robust 2D containment/boolean operations.
        outline_points = plate_outline.points
        if len(outline_points) > 2 and outline_points[0] == outline_points[-1]:
            outline_points = outline_points[:-1]
        plate_outline = Polygon(outline_points)

        # NOTE: spacing is handled by the nesting algorithms when choosing positions.
        # Keep `add_element` as a pure geometric containment/write operation.
        if not self.can_fit_element(plate_outline):
            raise ValueError("Plate doesn't fit in remaining space")

        # Update remaining boundary using boolean difference
        difference_result = self._remaining_boundary.boolean_difference(plate_outline)
        if difference_result:
            # Keep polygon boundaries only; boolean ops can return mixed geometry types.
            polygons = [item for item in difference_result if isinstance(item, Polygon)]
            if polygons:
                # Keep the largest remainder as current boundary.
                self._remaining_boundary = max(polygons, key=lambda p: p.area)

        # Store BTLx-oriented frame for export in element_data.
        self.element_data[str(plate.guid)] = NestedElementData(
            frame=self._to_btlx_partref_frame(placement_frame),
            key=plate.name + "-" + str(plate.guid)[:4],
        )
        # Preserve raw placement frame for Rhino-side visualization/debug.
        self.placement_data[str(plate.guid)] = placement_frame
        # Track used area directly because boolean remaining boundaries can degrade
        # to non-polygon results in some edge cases.
        self._used_area += plate.blank.xsize * plate.blank.ysize

    @staticmethod
    def _to_btlx_partref_frame(placement_frame):
        """Convert XY nesting placement frame to BTLx rawpart convention frame.

        BTLx rawparts use X as length, Y as height (thickness), Z as width.
        2D nesting coordinates are on XY, so we map nesting Y -> BTLx Z.
        """
        point = Point(placement_frame.point.x, 0.0, placement_frame.point.y)

        xaxis_xy = placement_frame.xaxis
        xaxis = Vector(xaxis_xy.x, 0.0, xaxis_xy.y)
        if xaxis.length < TOL.absolute:
            xaxis = Vector(1, 0, 0)

        yaxis = Vector(0, 1, 0)
        return Frame(point, xaxis, yaxis)


class NestingResult(Data):
    """
    A wrapper class for nesting results that provides serialization capabilities.

    Parameters
    ----------
    stocks : list[:class:`Stock`]
        List of stock pieces with assigned beams
    tolerance : :class:`~compas.tolerance.Tolerance`, optional
        The tolerance configuration used for this model. TOL if none provided.
    Attributes
    ----------
    stocks : list[:class:`Stock`]
        List of stock pieces with assigned beams
    tolerance : :class:`~compas.tolerance.Tolerance`
        The tolerance configuration used for this model. TOL if none provided.
    unplaced_elements : list[str]
        GUIDs of elements that could not be nested
    unplaced_reasons : dict[str, str]
        Optional reason labels keyed by unplaced GUID
    seed : int | None
        Seed used for seeded nesting variants (if provided)
    effective_spacing : float | None
        Effective spacing used by nesting (may be epsilon-adjusted)
    total_material_volume : float
        Total material volume across all stocks in cubic millimeters
    total_stock_pieces : dict
        Detailed report of stock pieces needed with their dimensions
    stock_utilization : list[dict]
        Per-stock utilization metrics and capacity usage
    summary : str
        Human-readable summary of the nesting result
    """

    def __init__(self, stocks, tolerance=None, unplaced_elements=None, seed=None, unplaced_reasons=None, effective_spacing=None):
        super(NestingResult, self).__init__()
        self.stocks = stocks if isinstance(stocks, list) else [stocks]
        self._tolerance = tolerance or TOL
        self.unplaced_elements = list(unplaced_elements or [])
        self.seed = seed
        self.unplaced_reasons = dict(unplaced_reasons or {})
        self.effective_spacing = effective_spacing

    @property
    def tolerance(self):
        return self._tolerance

    @property
    def __data__(self):
        return {
            "stocks": self.stocks,
            "tolerance": self.tolerance,
            "unplaced_elements": self.unplaced_elements,
            "seed": self.seed,
            "unplaced_reasons": self.unplaced_reasons,
            "effective_spacing": self.effective_spacing,
        }

    @property
    def unplaced_count(self):
        """Number of elements that could not be nested."""
        return len(self.unplaced_elements)

    @property
    def total_material_volume(self):
        """Calculate total material volume across all stocks in cubic millimeters."""
        return sum(stock.length * stock.width * stock.height for stock in self.stocks)

    @property
    def total_stock_pieces(self):
        """Generate a detailed report of stock pieces needed with their dimensions."""
        stock_report = {}

        for stock in self.stocks:
            if isinstance(stock, BeamStock):
                # Format: "60x120x2000mm" (width x height x length)
                dimensions_key = "Dimensions({}): {:.{prec}f}x{:.{prec}f}x{:.{prec}f}".format(
                    self.tolerance.unit, float(stock.cross_section[0]), float(stock.cross_section[1]), float(stock.length), prec=self.tolerance.precision
                )
                stock_type = "BeamStock"
            elif isinstance(stock, PlateStock):
                # Format: "1200x2400x18mm" (length x width x thickness)
                dimensions_key = "Dimensions({}): {:.{prec}f}x{:.{prec}f}x{:.{prec}f}".format(
                    self.tolerance.unit, float(stock.dimensions[0]), float(stock.dimensions[1]), float(stock.thickness), prec=self.tolerance.precision
                )
                stock_type = "PlateStock"
            else:
                # Fallback for other stock types
                dimensions_key = "Dimensions({}): {:.{prec}f}x{:.{prec}f}x{:.{prec}f}".format(
                    self.tolerance.unit, float(stock.length), float(stock.width), float(stock.height), prec=self.tolerance.precision
                )
                stock_type = type(stock).__name__

            # Create nested structure: {stock_type: {dimensions: count}}
            if stock_type not in stock_report:
                stock_report[stock_type] = {}

            if dimensions_key not in stock_report[stock_type]:
                stock_report[stock_type][dimensions_key] = 0

            stock_report[stock_type][dimensions_key] += 1

        return stock_report

    @property
    def summary(self):
        """Return a human-readable summary of the nesting result."""
        lines = []
        for i, stock in enumerate(self.stocks):
            lines.append(f"{stock.__class__.__name__}_{i}:")
            if isinstance(stock, BeamStock):
                lines.append(
                    "Dimensions({}): {:.{prec}f}x{:.{prec}f}x{:.{prec}f}".format(
                        self.tolerance.unit, float(stock.cross_section[0]), float(stock.cross_section[1]), float(stock.length), prec=self.tolerance.precision
                    )
                )
                beam_keys = []
                lengths = []
                for data in stock.element_data.values():
                    beam_keys.append(data.key)
                    lengths.append(data.length)
                formatted_lengths = ["{:.{prec}f}".format(len, prec=self.tolerance.precision) for len in lengths]
                waste = stock.length - sum(lengths) if lengths else stock.length
                # Formatted output
                lines.append(f"BeamKeys: {beam_keys}")
                lines.append("BeamLengths({}): [{}]".format(self.tolerance.unit, ", ".join(formatted_lengths)))
                lines.append("Waste({}): {:.{prec}f}".format(self.tolerance.unit, waste, prec=self.tolerance.precision))
                lines.append("Spacing({}): {:.{prec}f}".format(self.tolerance.unit, float(stock.spacing), prec=self.tolerance.precision))
                lines.append("--------")
            else:
                raise NotImplementedError("Formatted summary not implemented for this stock type yet.")
        return "\n".join(lines)

    @property
    def stock_utilization(self):
        """Generate per-stock utilization metrics.

        Returns
        -------
        list[dict]
            A list of dictionaries with per-stock metrics:
            ``stock_index``, ``stock_type``, ``utilization_percent``,
            ``capacity``, ``used``, ``remaining``, and ``element_count``.
        """
        metrics = []

        for i, stock in enumerate(self.stocks):
            if isinstance(stock, BeamStock):
                capacity = float(stock.length)
                # BeamStock tracks next start position and includes spacing increment
                # after each inserted beam. Remove one spacing for utilization.
                if stock.element_data:
                    used = max(0.0, min(capacity, stock._current_x_position - stock.spacing))
                else:
                    used = 0.0
                remaining = max(0.0, capacity - used)
                utilization = 100.0 * used / capacity if capacity > TOL.absolute else 0.0
                metrics.append(
                    {
                        "stock_index": i,
                        "stock_type": "BeamStock",
                        "utilization_percent": utilization,
                        "capacity": capacity,
                        "used": used,
                        "remaining": remaining,
                        "element_count": len(stock.element_data),
                    }
                )
                continue

            if isinstance(stock, PlateStock):
                capacity = float(stock.dimensions[0] * stock.dimensions[1])
                if hasattr(stock, "_used_area"):
                    used = max(0.0, min(capacity, float(stock._used_area)))
                else:
                    used = max(0.0, min(capacity, capacity - stock._remaining_area))
                remaining = max(0.0, capacity - used)
                utilization = 100.0 * used / capacity if capacity > TOL.absolute else 0.0
                metrics.append(
                    {
                        "stock_index": i,
                        "stock_type": "PlateStock",
                        "utilization_percent": utilization,
                        "capacity": capacity,
                        "used": used,
                        "remaining": remaining,
                        "element_count": len(stock.element_data),
                    }
                )
                continue

            # Generic fallback for unknown stock implementations.
            capacity = float(stock.length * stock.width * stock.height)
            metrics.append(
                {
                    "stock_index": i,
                    "stock_type": type(stock).__name__,
                    "utilization_percent": None,
                    "capacity": capacity,
                    "used": None,
                    "remaining": None,
                    "element_count": len(stock.element_data),
                }
            )

        return metrics

    @property
    def report_data(self):
        """Return a compact nesting report payload."""
        return {
            "total_stock_pieces": self.total_stock_pieces,
            "total_material_volume": self.total_material_volume,
            "stock_utilization": self.stock_utilization,
            "unplaced_elements": self.unplaced_elements,
            "unplaced_reasons": self.unplaced_reasons,
            "unplaced_count": self.unplaced_count,
            "seed": self.seed,
            "effective_spacing": self.effective_spacing,
        }


class BeamNester(object):
    """
    A class for optimizing 1D nesting of beams into stock pieces.

    This class implements algorithms to efficiently nest beams from a TimberModel
    into available stock pieces, minimizing waste and cost.

    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        The timber model containing beams to nest
    stock_catalog : list[:class:`BeamStock`]
        Available BeamStock pieces for nesting.
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.)
    per_group : bool, optional
        Whether to nest beams per group or all together. Default is False (all together).

    Attributes
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        The timber model
    stock_catalog : list[:class:`BeamStock`]
        Available BeamStock pieces for nesting
    spacing : float
        Spacing tolerance for cutting operations (kerf width, etc.)
    per_group : bool
        Whether to nest beams per group or all together. Default is False (all together).
    """

    def __init__(self, model, stock_catalog, spacing=0.0, per_group=False):
        self.model = model
        self.spacing = spacing
        self.per_group = per_group
        self.stock_catalog = stock_catalog if isinstance(stock_catalog, list) else [stock_catalog]

    @property
    def stock_catalog(self):
        """Get the stock catalog."""
        return self._stock_catalog

    @stock_catalog.setter
    def stock_catalog(self, value):
        """Set the stock catalog with validation."""
        # Validate that all items are BeamStock instances
        for i, stock in enumerate(value):
            if not isinstance(stock, BeamStock):
                raise TypeError(f"All items in stock_catalog must be BeamStock instances. Item at index {i} is {type(stock).__name__}")
        self._stock_catalog = value

    def nest(self, fast=True):
        """
        Perform 1D nesting of all beams in the model.

        Parameters
        ----------
        fast : bool, optional
            Whether to use a fast nesting algorithm (First Fit Decreasing) or a more
            accurate one (Best Fit Decreasing). Default is True (fast).

        Returns
        -------
        :class:`NestingResult`
            Nesting result containing stocks with assigned beams and metadata
        """
        nesting_stocks = []
        if self.per_group:
            # Collect beam groups
            beam_groups = []  # list of lists of beams per group
            standalone_beams = []
            for element in self.model.elements():
                if element.is_group_element:
                    group_children = list(self.model.get_elements_in_group(element, filter_=lambda e: e.is_beam))
                    if group_children:
                        beam_groups.append(group_children)

                elif element.is_beam and element.parent is None:
                    # Handle standalone beams not in a group
                    standalone_beams.append(element)
            if standalone_beams:
                beam_groups.append(standalone_beams)

            # Nest each group separately
            for beams in beam_groups:
                stocks = self._nest_beam_collection(beams, fast)
                nesting_stocks.extend(stocks)
        else:
            # Nest ALL beams together
            stocks = self._nest_beam_collection(self.model.beams, fast)
            nesting_stocks.extend(stocks)

        return NestingResult(nesting_stocks, tolerance=self.model.tolerance)

    def _nest_beam_collection(self, beams, fast=True):
        # Nest a collection of beams into stock pieces.
        stocks = []
        stock_beam_map = self._sort_beams_by_stock(beams)

        for stock_type, compatible_beams in stock_beam_map.items():
            if not compatible_beams:
                continue
            # Apply selected algorithm
            if fast:
                result_stocks = self._first_fit_decreasing(compatible_beams, stock_type, self.spacing)
            else:
                result_stocks = self._best_fit_decreasing(compatible_beams, stock_type, self.spacing)

            stocks.extend(result_stocks)
        return stocks

    def _sort_beams_by_stock(self, beams):
        # Sort beams into compatible stock types based on their dimensions.
        unnested_beams = []
        stock_beam_map = {stock: [] for stock in self.stock_catalog}
        for beam in beams:
            beam_matched = False
            for stock in self.stock_catalog:
                if stock.is_compatible_with(beam):
                    stock_beam_map[stock].append(beam)
                    beam_matched = True
                    break  # Assign beam to first compatible stock type

            if not beam_matched:
                unnested_beams.append(beam)

        if unnested_beams:
            # Collect unique cross-sections from unnested beams
            beam_details = set((beam.width, beam.height) for beam in unnested_beams)
            # Format each cross-section as a string
            formatted_sections = ["{}x{}{}".format(width, height, self.model.tolerance.unit) for width, height in beam_details]

            warn(
                "Found {} beam(s) incompatible with available stock catalog. Beams with the following cross-sections will be skipped during nesting: {}".format(  # noqa: E501
                    len(unnested_beams), ", ".join(formatted_sections)
                )
            )
        return stock_beam_map

    @staticmethod
    def _first_fit_decreasing(beams, stock, spacing=0.0):
        # Fast but more wasteful packing
        # Places each beam in the first stock that has enough space, without optimizing for minimal waste.
        sorted_beams = sorted(beams, key=lambda b: b.blank_length, reverse=True)

        stocks = []
        for beam in sorted_beams:
            # Try to fit in existing stocks
            fitted = False
            for stock_piece in stocks:
                if stock_piece.can_fit_element(beam):
                    stock_piece.add_element(beam)
                    fitted = True
                    break
            # If not fitted, create new stock
            if not fitted:
                new_stock = BeamStock(stock.length, stock.cross_section, spacing=spacing)
                new_stock.add_element(beam)
                stocks.append(new_stock)

        return stocks

    @staticmethod
    def _best_fit_decreasing(beams, stock, spacing=0.0):
        # Slower but more efficient packing
        # Minimizes waste by selecting the stock piece with the smallest remaining space that can still fit the beam.
        sorted_beams = sorted(beams, key=lambda b: b.blank_length, reverse=True)

        stocks = []
        for beam in sorted_beams:
            # Find best fitting existing stock (smallest waste that still fits)
            best_stock = None
            best_waste = float("inf")

            for stock_piece in stocks:
                if stock_piece.can_fit_element(beam) and stock_piece._remaining_length < best_waste:
                    best_waste = stock_piece._remaining_length
                    best_stock = stock_piece
            # If found a fitting stock, use it
            if best_stock is not None:
                best_stock.add_element(beam)
            else:
                # Create new stock
                new_stock = BeamStock(stock.length, stock.cross_section, spacing=spacing)
                new_stock.add_element(beam)
                stocks.append(new_stock)

        return stocks


class PlateNester(object):
    """
    A class for optimizing 2D nesting of plates into stock pieces.

    This class implements algorithms to efficiently nest plates from a TimberModel
    into available stock pieces, minimizing waste and cost.

    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        The timber model containing plates to nest
    stock_catalog : list[:class:`PlateStock`]
        Available PlateStock pieces for nesting.
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.)
    per_group : bool, optional
        Whether to nest plates per group or all together. Default is False (all together).
    seed : int, optional
        Seed for reproducible variant generation. Different seeds can produce
        different placement orders for the same pieces.

    Attributes
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        The timber model
    stock_catalog : list[:class:`PlateStock`]
        Available PlateStock pieces for nesting
    spacing : float
        Spacing tolerance for cutting operations (kerf width, etc.)
    per_group : bool
        Whether to nest plates per group or all together. Default is False (all together).
    seed : int | None
        Seed for reproducible variant generation.
    """

    def __init__(self, model, stock_catalog, spacing=0.0, per_group=False, seed=None):
        self.model = model
        self.spacing = spacing
        self.per_group = per_group
        self.seed = seed
        self.stock_catalog = stock_catalog if isinstance(stock_catalog, list) else [stock_catalog]

    @property
    def stock_catalog(self):
        """Get the stock catalog."""
        return self._stock_catalog

    @stock_catalog.setter
    def stock_catalog(self, value):
        """Set the stock catalog with validation."""
        # Validate that all items are PlateStock instances
        for i, stock in enumerate(value):
            if not isinstance(stock, PlateStock):
                raise TypeError(f"All items in stock_catalog must be PlateStock instances. Item at index {i} is {type(stock).__name__}")
        self._stock_catalog = value

    def nest(self, fast=True):
        """
        Perform 2D nesting of all plates in the model.

        Parameters
        ----------
        fast : bool, optional
            Whether to use a fast nesting algorithm (Skyline with bounding boxes) or a more
            accurate one (Bottom-Left with polygon geometry). Default is True (fast).

        Returns
        -------
        :class:`NestingResult`
            Nesting result containing stocks with assigned plates and metadata
        """
        nesting_stocks = []
        unplaced_plate_guids = []
        unplaced_reasons = {}
        effective_spacing = self.spacing if self.spacing > TOL.absolute else TOL.absolute
        if self.per_group:
            # Collect plate groups
            plate_groups = []  # list of lists of plates per group
            standalone_plates = []
            for element in self.model.elements():
                if element.is_group_element:
                    group_children = list(self.model.get_elements_in_group(element, filter_=lambda e: e.is_plate))
                    if group_children:
                        plate_groups.append(group_children)

                elif element.is_plate and element.parent is None:
                    # Handle standalone plates not in a group
                    standalone_plates.append(element)
            if standalone_plates:
                plate_groups.append(standalone_plates)

            # Nest each group separately
            for group_index, plates in enumerate(plate_groups):
                group_seed = None if self.seed is None else self.seed + group_index
                stocks, unplaced, reasons = self._nest_plate_collection(plates, fast, seed=group_seed)
                nesting_stocks.extend(stocks)
                unplaced_plate_guids.extend(unplaced)
                unplaced_reasons.update(reasons)
        else:
            # Nest ALL plates together
            stocks, unplaced, reasons = self._nest_plate_collection(self.model.plates, fast, seed=self.seed)
            nesting_stocks.extend(stocks)
            unplaced_plate_guids.extend(unplaced)
            unplaced_reasons.update(reasons)

        return NestingResult(
            nesting_stocks,
            unplaced_elements=unplaced_plate_guids,
            seed=self.seed,
            unplaced_reasons=unplaced_reasons,
            effective_spacing=effective_spacing,
        )

    def _nest_plate_collection(self, plates, fast=True, seed=None):
        # Nest a collection of plates into stock pieces.
        stocks = []
        unplaced = []
        unplaced_reasons = {}
        stock_plate_map, incompatible_plates = self._sort_plates_by_stock(plates)
        for plate in incompatible_plates:
            guid = str(plate.guid)
            unplaced.append(guid)
            unplaced_reasons[guid] = "incompatible_stock"

        # Keep exact user spacing semantics for positive spacing, and use a tiny
        # numerical clearance to avoid degenerate boolean/same-edge failures at 0.
        spacing = self.spacing if self.spacing > TOL.absolute else TOL.absolute

        rng = random.Random(seed) if seed is not None else None

        for stock_type, compatible_plates in stock_plate_map.items():
            if not compatible_plates:
                continue
            # Apply selected algorithm
            if fast:
                result_stocks, unplaced_plates = self._fast_skyline_nest(compatible_plates, stock_type, spacing, rng=rng, return_unplaced=True)
            else:
                result_stocks, unplaced_plates = self._optimized_bottomleft_nest(compatible_plates, stock_type, spacing, rng=rng, return_unplaced=True)

            stocks.extend(result_stocks)
            for plate, reason in unplaced_plates:
                guid = str(plate.guid)
                unplaced.append(guid)
                unplaced_reasons[guid] = reason
        return stocks, unplaced, unplaced_reasons

    def _sort_plates_by_stock(self, plates):
        # Sort plates into compatible stock types based on their dimensions.
        unnested_plates = []
        stock_plate_map = {stock: [] for stock in self.stock_catalog}
        for plate in plates:
            plate_matched = False
            for stock in self.stock_catalog:
                if stock.is_compatible_with(plate):
                    stock_plate_map[stock].append(plate)
                    plate_matched = True
                    break  # Assign plate to first compatible stock type

            if not plate_matched:
                unnested_plates.append(plate)

        if unnested_plates:
            # Collect unique thicknesses from unnested plates
            plate_details = set(plate.thickness for plate in unnested_plates)
            # Format each thickness as a string
            formatted_thicknesses = ["{}mm".format(int(thickness)) for thickness in plate_details]

            warn(
                "Found {} plate(s) incompatible with available stock catalog. Plates with the following thicknesses will be skipped during nesting: {}".format(
                    len(unnested_plates), ", ".join(formatted_thicknesses)
                )
            )
        return stock_plate_map, unnested_plates

    @classmethod
    def _plate_orientations(cls, plate):
        """Return candidate dimensions in both orientations.

        Returns
        -------
        list[tuple[float, float, bool]]
            Tuples of (width, height, rotated).
        """
        return [
            (plate.blank.xsize, plate.blank.ysize, False),
            (plate.blank.ysize, plate.blank.xsize, True),
        ]

    @classmethod
    def _plate_sort_key(cls, plate):
        """Deterministic descending sort key for plate placement order."""
        width = plate.blank.xsize
        height = plate.blank.ysize
        area = width * height
        perimeter = width + height
        return (-area, -perimeter, -max(width, height), str(plate.guid))

    @classmethod
    def _ordered_plates(cls, plates, rng=None):
        """Return plate order for placement.

        Without a seed, placement order is deterministic and area-driven.
        With a seed, order is reproducibly shuffled to explore alternatives.
        """
        ordered = list(plates)
        if rng is None:
            return sorted(ordered, key=cls._plate_sort_key)
        rng.shuffle(ordered)
        return ordered

    @classmethod
    def _placement_transformation(cls, position, plate_width, rotated, spacing):
        """Build placement transformation from skyline position."""
        half_spacing = spacing * 0.5
        if rotated:
            rotation = Rotation.from_axis_and_angle(Vector(0, 0, 1), math.pi / 2)
            translation = Translation.from_vector(Vector(position.x + half_spacing + plate_width, position.y + half_spacing, 0))
            return translation * rotation
        return Translation.from_vector(Vector(position.x + half_spacing, position.y + half_spacing, 0))

    @classmethod
    def _best_skyline_candidate(cls, stock_piece, orientations, spacing, prioritize_bottomleft=False):
        """Find the best skyline candidate across orientations for a stock piece."""
        best = None
        segments = cls._skyline_segments(stock_piece)

        # lightweight state tracking for fast fit scoring.
        current_max_x = getattr(stock_piece, "_used_max_x", 0.0)
        current_max_y = getattr(stock_piece, "_used_max_y", 0.0)

        for plate_width, plate_height, rotated in orientations:
            footprint_w = plate_width + spacing
            footprint_h = plate_height + spacing

            position, waste, envelope_area = cls._find_skyline_position(
                stock_piece,
                footprint_w,
                footprint_h,
                segments=segments,
                current_max_x=current_max_x,
                current_max_y=current_max_y,
                prioritize_bottomleft=prioritize_bottomleft,
            )

            if position is None:
                continue

            if prioritize_bottomleft:
                key = (position.y, position.x, envelope_area, waste)
            else:
                key = (envelope_area, waste, position.y, position.x)

            if best is None or key < best[0]:
                best = (key, position, plate_width, plate_height, footprint_w, footprint_h, rotated)
        return best

    @classmethod
    def _warn_unplaceable_plate(cls, plate, stock, spacing):
        """Emit a consistent warning when a plate cannot be placed on stock."""
        warn(
            "Plate {}x{}mm cannot fit in stock {}x{}mm (with spacing {}).".format(
                plate.blank.xsize,
                plate.blank.ysize,
                stock.dimensions[0],
                stock.dimensions[1],
                spacing,
            )
        )

    @classmethod
    def _fast_skyline_nest(cls, plates, stock, spacing=0.0, rng=None, return_unplaced=False):
        """Fast skyline packing using plate bounding boxes.

        Plates are processed by decreasing area and placed in the best skyline
        candidate across both orientations.
        """

        sorted_plates = cls._ordered_plates(plates, rng=rng)

        stocks = []
        unplaced = []
        for plate in sorted_plates:
            placed = False
            orientations = cls._plate_orientations(plate)

            # Try to fit in existing stocks
            for stock_piece in stocks:
                best = cls._best_skyline_candidate(stock_piece, orientations, spacing, prioritize_bottomleft=False)

                if best is None:
                    continue

                _, position, plate_width, plate_height, footprint_w, footprint_h, rotated = best
                transformation = cls._placement_transformation(position, plate_width, rotated, spacing)

                try:
                    stock_piece.add_element(plate, transformation)
                    cls._update_skyline(stock_piece, position, footprint_w, footprint_h)
                    placed = True
                    break
                except ValueError:
                    # Candidate may be invalid with exact polygon geometry; try next candidate/stock.
                    continue

            # Create new stock if not placed
            if not placed:
                new_stock = PlateStock(stock.dimensions, stock.thickness, spacing=spacing)
                best = cls._best_skyline_candidate(new_stock, orientations, spacing, prioritize_bottomleft=False)

                if best is not None:
                    _, position, plate_width, plate_height, footprint_w, footprint_h, rotated = best
                    transformation = cls._placement_transformation(position, plate_width, rotated, spacing)

                    try:
                        new_stock.add_element(plate, transformation)
                        cls._update_skyline(new_stock, position, footprint_w, footprint_h)
                        stocks.append(new_stock)
                    except ValueError:
                        warn("Plate {}x{}mm could not be placed on a new stock despite skyline candidate.".format(plate.blank.xsize, plate.blank.ysize))
                        unplaced.append((plate, "geometry_fit_failed"))
                else:
                    cls._warn_unplaceable_plate(plate, stock, spacing)
                    unplaced.append((plate, "no_skyline_candidate"))

        if return_unplaced:
            return stocks, unplaced
        return stocks

    @classmethod
    def _skyline_segments(cls, stock):
        """Convert skyline polyline to horizontal segments (start_x, end_x, y)."""
        segments = []
        points = stock._skyline.points
        for i in range(len(points) - 1):
            a = points[i]
            b = points[i + 1]
            if TOL.is_close(a.y, b.y) and b.x > a.x:
                segments.append((a.x, b.x, a.y))
        return segments

    @classmethod
    def _candidate_x_positions(cls, segments, plate_width, stock_width):
        """Generate deterministic skyline x-candidates for a footprint width."""
        max_x = stock_width - plate_width
        if max_x < -TOL.absolute:
            return []

        candidates = {0.0}
        for sx, ex, _ in segments:
            candidates.add(sx)
            candidates.add(ex - plate_width)

        valid = []
        for x in candidates:
            if x < -TOL.absolute:
                continue
            if x > max_x + TOL.absolute:
                continue
            clamped_x = max(0.0, min(x, max_x))
            valid.append(clamped_x)

        return sorted(set(valid))

    @classmethod
    def _find_skyline_position(
        cls,
        stock,
        plate_width,
        plate_height,
        segments=None,
        current_max_x=0.0,
        current_max_y=0.0,
        prioritize_bottomleft=False,
    ):
        """Find the best skyline position for a rectangular footprint.

        Returns
        -------
        tuple[:class:`compas.geometry.Point` | None, float, float]
            Candidate position, skyline waste metric, and resulting envelope area.
            Returns ``(None, inf, inf)`` when no valid position exists.
        """

        best_position = None
        best_waste = float("inf")
        best_area = float("inf")
        best_key = None

        if segments is None:
            segments = cls._skyline_segments(stock)

        # Try deterministic skyline candidates derived from segment starts/ends.
        for x in cls._candidate_x_positions(segments, plate_width, stock.dimensions[0]):

            # Check if plate fits at this position
            if x + plate_width > stock.dimensions[0]:
                continue  # Doesn't fit horizontally

            # Base Y is the max skyline height over the plate footprint span.
            y = 0.0
            for sx, ex, sy in segments:
                if ex <= x or sx >= x + plate_width:
                    continue
                y = max(y, sy)

            if y + plate_height > stock.dimensions[1]:
                continue  # Doesn't fit vertically

            # Calculate waste (height difference to next skyline segment)
            waste = cls._calculate_skyline_waste(segments, x, plate_width, y)

            # Prefer candidates that keep the global used envelope compact.
            envelope_area = max(current_max_x, x + plate_width) * max(current_max_y, y + plate_height)

            # Create test position
            test_position = Point(x, y, 0)

            # Create test rectangle polygon for validation
            test_rect = Polygon([Point(x, y, 0), Point(x + plate_width, y, 0), Point(x + plate_width, y + plate_height, 0), Point(x, y + plate_height, 0)])

            # Check if this candidate fits using stock fit logic
            if stock.can_fit_element(test_rect):
                if prioritize_bottomleft:
                    candidate_key = (y, x, envelope_area, waste)
                else:
                    candidate_key = (envelope_area, waste, y, x)

                if best_key is None or candidate_key < best_key:
                    best_key = candidate_key
                    best_position = test_position
                    best_waste = waste
                    best_area = envelope_area

        return best_position, best_waste, best_area

    @classmethod
    def _calculate_skyline_waste(cls, segments, x, width, base_y):
        """Calculate skyline waste over a covered horizontal interval."""

        waste = 0

        for segment_start_x, segment_end_x, segment_y in segments:
            # Check if this segment is in the covered region
            if segment_start_x >= x + width:
                break  # Past the covered region

            if segment_end_x <= x:
                continue  # Before the covered region

            # This segment overlaps with the placement region
            overlap_start = max(segment_start_x, x)
            overlap_end = min(segment_end_x, x + width)
            overlap_width = overlap_end - overlap_start

            # Add height difference as waste
            height_diff = abs(segment_y - base_y)
            waste += height_diff * overlap_width

        return waste

    @classmethod
    def _update_skyline(cls, stock, position, plate_width, plate_height):
        """Update skyline profile after reserving a rectangular footprint."""
        x = position.x
        x2 = x + plate_width
        new_y = position.y + plate_height

        # Keep compact used-envelope state for candidate scoring.
        stock._used_max_x = max(getattr(stock, "_used_max_x", 0.0), x2)
        stock._used_max_y = max(getattr(stock, "_used_max_y", 0.0), new_y)

        old_segments = cls._skyline_segments(stock)
        new_segments = []

        # Clip existing skyline by removing the covered interval [x, x2]
        for sx, ex, sy in old_segments:
            if ex <= x or sx >= x2:
                new_segments.append([sx, ex, sy])
                continue
            if sx < x:
                new_segments.append([sx, x, sy])
            if ex > x2:
                new_segments.append([x2, ex, sy])

        # Add raised segment for the placed plate
        new_segments.append([x, x2, new_y])
        new_segments.sort(key=lambda seg: seg[0])

        # Merge adjacent segments with same height
        merged = []
        for sx, ex, sy in new_segments:
            if merged and TOL.is_close(merged[-1][1], sx) and TOL.is_close(merged[-1][2], sy):
                merged[-1][1] = ex
            else:
                merged.append([sx, ex, sy])

        # Rebuild skyline polyline with vertical steps between horizontal segments
        if not merged:
            stock._skyline = Polyline([[0, 0, 0], [stock.dimensions[0], 0, 0]])
            return

        points = [[merged[0][0], merged[0][2], 0], [merged[0][1], merged[0][2], 0]]
        prev_ex = merged[0][1]
        prev_y = merged[0][2]

        for sx, ex, sy in merged[1:]:
            if sx > prev_ex:
                points.append([sx, prev_y, 0])
            if not TOL.is_close(sy, prev_y):
                points.append([sx, sy, 0])
            points.append([ex, sy, 0])
            prev_ex = ex
            prev_y = sy

        # Remove duplicate consecutive points
        cleaned = []
        for pt in points:
            if not cleaned or cleaned[-1] != pt:
                cleaned.append(pt)

        stock._skyline = Polyline(cleaned)

    @classmethod
    def _optimized_bottomleft_nest(cls, plates, stock, spacing=0.0, rng=None, return_unplaced=False):
        """Bottom-left skyline strategy prioritizing lower-left placements.

        Uses the same candidate generator as the fast method, but ranks solutions
        by minimal ``y`` first and ``x`` second.
        """
        sorted_plates = cls._ordered_plates(plates, rng=rng)

        stocks = []
        unplaced = []

        for plate in sorted_plates:
            best = None  # tuple(rank_key, stock_piece, position, rotated, plate_width, plate_height, footprint_w, footprint_h)
            orientations = cls._plate_orientations(plate)

            # Try existing stock pieces first
            for stock_piece in stocks:
                candidate = cls._best_skyline_candidate(stock_piece, orientations, spacing, prioritize_bottomleft=True)
                if candidate is None:
                    continue
                rank_key, position, plate_width, plate_height, footprint_w, footprint_h, rotated = candidate
                if best is None or rank_key < best[0]:
                    best = (rank_key, stock_piece, position, rotated, plate_width, plate_height, footprint_w, footprint_h)

            if best is not None:
                _, stock_piece, position, rotated, plate_width, plate_height, footprint_w, footprint_h = best
                transformation = cls._placement_transformation(position, plate_width, rotated, spacing)
                stock_piece.add_element(plate, transformation)
                cls._update_skyline(stock_piece, position, footprint_w, footprint_h)
                continue

            # If not placed, create a new stock and try from origin using skyline search
            new_stock = PlateStock(stock.dimensions, stock.thickness, spacing=spacing)
            candidate = cls._best_skyline_candidate(new_stock, orientations, spacing, prioritize_bottomleft=True)
            if candidate is not None:
                _, position, plate_width, plate_height, footprint_w, footprint_h, rotated = candidate
                transformation = cls._placement_transformation(position, plate_width, rotated, spacing)
                new_stock.add_element(plate, transformation)
                cls._update_skyline(new_stock, position, footprint_w, footprint_h)
                stocks.append(new_stock)
            else:
                cls._warn_unplaceable_plate(plate, stock, spacing)
                unplaced.append((plate, "no_skyline_candidate"))

        if return_unplaced:
            return stocks, unplaced
        return stocks

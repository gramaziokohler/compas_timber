from abc import ABC
from abc import abstractmethod
from warnings import warn

from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polygon
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import is_polygon_in_polygon_xy
from compas.geometry import offset_polygon
from compas.tolerance import TOL


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
    element_data : dict[str, Frame], optional
        Dictionary mapping element GUIDs to their assigned position frames.

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
    element_data : dict[str, Frame]
        Dictionary mapping element GUIDs to their assigned position frames.
    """

    def __init__(self, length, width, height, spacing=0.0, element_data=None):
        super(Stock, self).__init__()
        self.length = length
        self.width = width
        self.height = height
        self.spacing = spacing
        self.element_data = element_data or {}  # {guid: Frame}

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
    element_data : dict[str, Frame], optional
        Dictionary mapping element GUIDs to their assigned position frames.


    Attributes
    ----------
    length : float
        Length of the stock piece.
    cross_section : tuple of float
        Cross-section dimensions sorted in ascending order for consistent comparison.
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, Frame], optional
        Dictionary mapping element GUIDs to their assigned position frames.
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
        beam_cross_section = [beam.width, beam.height]
        return set(beam_cross_section) == set(self.cross_section)

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
            raise ValueError(f"Beam with length {beam.blank_length} doesn't fit in remaining space {self._remaining_length}")
        # Get position frame based on orientation
        position_frame = self._get_position_frame(beam)
        # Store element data
        self.element_data[str(beam.guid)] = position_frame
        self._current_x_position += beam.blank_length + self.spacing  # Update position for next beam

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
    element_data : dict[str, Frame], optional
        Dictionary mapping element GUIDs to their assigned position frames.

    Attributes
    ----------
    dimensions : tuple of float
        Dimensions of the stock piece (length, width).
    thickness : float
        Thickness of the stock piece
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, Frame], optional
        Dictionary mapping element GUIDs to their assigned position frames.
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

    @property
    def __data__(self):
        data = super(PlateStock, self).__data__
        data["dimensions"] = self.dimensions
        data["thickness"] = self.thickness
        return data

    @property
    def _remaining_area(self):
        # Get remaining available area in the stock.
        return self._remaining_boundary.area

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
        # TODO: Signature mismatch with abstract Stock.can_fit_element(element)
        # TODO: Should accept plate object + transformation instead of pre-transformed polygon
        # TODO: This prevents proper validation before algorithms find positions

        # Step 1: Quick area rejection
        if plate_outline.area > self._remaining_area:
            return False
        # Step 2: Shape check
        return is_polygon_in_polygon_xy(plate_outline, self._remaining_boundary)

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
        # Get frame from transformation
        position_frame = Frame.from_transformation(transformation)

        # Transform plate polygon outline to placement position
        plate_outline = plate.local_outline_a.transformed(transformation)  # TODO: check which one of the two to use

        # TODO: Offset timing issue - spacing should be applied during fit check, not just here
        # TODO: This means can_fit_element needs access to spacing and transformation
        # Offset polygon by spacing to account for cutting tolerance
        plate_outline = offset_polygon(plate_outline, self.spacing)

        # TODO: This validation happens AFTER offset, but algorithm needs to know BEFORE finding position
        if not self.can_fit_element(plate_outline):
            raise ValueError("Plate doesn't fit in remaining space")

        # Update remaining boundary using boolean difference
        difference_result = self._remaining_boundary.boolean_difference(plate_outline)
        if difference_result:
            self._remaining_boundary = difference_result[0]

        # Store element data
        self.element_data[str(plate.guid)] = position_frame


class NestingResult(Data):
    """
    A wrapper class for nesting results that provides serialization capabilities.

    Parameters
    ----------
    stocks : list[:class:`Stock`]
        List of stock pieces with assigned beams

    Attributes
    ----------
    stocks : list[:class:`Stock`]
        List of stock pieces with assigned beams
    total_material_volume : float
        Total material volume across all stocks in cubic millimeters
    total_stock_pieces : dict
        Detailed report of stock pieces needed with their dimensions
    """

    def __init__(self, stocks):
        super(NestingResult, self).__init__()
        self.stocks = stocks if isinstance(stocks, list) else [stocks]

    @property
    def __data__(self):
        return {"stocks": self.stocks}

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
                dimensions_key = f"{int(stock.cross_section[0])}x{int(stock.cross_section[1])}x{int(stock.length)}" + "mm"
                stock_type = "BeamStock"
            elif isinstance(stock, PlateStock):
                # Format: "1200x2400x18mm" (length x width x thickness)
                dimensions_key = f"{int(stock.dimensions[0])}x{int(stock.dimensions[1])}x{int(stock.height)}" + "mm"
                stock_type = "PlateStock"
            else:
                # Fallback for other stock types
                dimensions_key = f"{int(stock.length)}x{int(stock.width)}x{int(stock.height)}" + "mm"
                stock_type = type(stock).__name__

            # Create nested structure: {stock_type: {dimensions: count}}
            if stock_type not in stock_report:
                stock_report[stock_type] = {}

            if dimensions_key not in stock_report[stock_type]:
                stock_report[stock_type][dimensions_key] = 0

            stock_report[stock_type][dimensions_key] += 1

        return stock_report


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

        return NestingResult(nesting_stocks)

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
            formatted_sections = ["{}x{}mm".format(int(width), int(height)) for width, height in beam_details]

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
            for plates in plate_groups:
                stocks = self._nest_plate_collection(plates, fast)
                nesting_stocks.extend(stocks)
        else:
            # Nest ALL plates together
            stocks = self._nest_plate_collection(self.model.plates, fast)
            nesting_stocks.extend(stocks)

        return NestingResult(nesting_stocks)

    def _nest_plate_collection(self, plates, fast=True):
        # Nest a collection of plates into stock pieces.
        stocks = []
        stock_plate_map = self._sort_plates_by_stock(plates)

        for stock_type, compatible_plates in stock_plate_map.items():
            if not compatible_plates:
                continue
            # Apply selected algorithm
            if fast:
                result_stocks = self._fast_skyline_nest(compatible_plates, stock_type, self.spacing)
            else:
                result_stocks = self._optimized_bottomleft_nest(compatible_plates, stock_type, self.spacing)

            stocks.extend(result_stocks)
        return stocks

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
        return stock_plate_map

    @staticmethod
    def _fast_skyline_nest(plates, stock, spacing=0.0):
        # Fast algorithm using bounding boxes and skyline approach.
        # Uses plate blank rectangles (xsize, ysize) for efficient packing.
        # Maintains a skyline profile to track the top edge of placed plates.

        # Sort plates by area (largest first) for better packing
        sorted_plates = sorted(plates, key=lambda p: p.blank.xsize * p.blank.ysize, reverse=True)

        stocks = []
        for plate in sorted_plates:
            # Get plate blank dimensions
            plate_width = plate.blank.xsize
            plate_height = plate.blank.ysize

            placed = False
            best_stock = None
            best_position = None
            best_waste = float("inf")

            # Try to fit in existing stocks
            for stock_piece in stocks:
                # Try to find position using skyline
                position, waste = PlateNester._find_skyline_position(stock_piece, plate_width, plate_height, spacing)

                if position is not None and waste < best_waste:
                    best_stock = stock_piece
                    best_position = position
                    best_waste = waste

            # Place plate in best stock found
            if best_stock is not None:
                # Create transformation from position
                transformation = Transformation.from_frame(Frame(best_position, [1, 0, 0], [0, 1, 0]))
                best_stock.add_element(plate, transformation)

                # Update skyline for this stock
                PlateNester._update_skyline(best_stock, best_position, plate_width, plate_height)
                placed = True

            # Create new stock if not placed
            if not placed:
                new_stock = PlateStock(stock.dimensions, stock.thickness, spacing=spacing)

                # Place at origin
                frame = Frame(Point(0, 0, 0), [1, 0, 0], [0, 1, 0])
                new_stock.add_element(plate, frame)

                # Update skyline
                PlateNester._update_skyline(new_stock, Point(0, 0, 0), plate_width, plate_height)
                stocks.append(new_stock)

        return stocks

    @staticmethod
    def _find_skyline_position(stock, plate_width, plate_height, spacing):
        # Find the best position on the skyline for a plate.
        # Returns (position, waste) or (None, inf) if no valid position found.

        best_position = None
        best_waste = float("inf")

        # Try each skyline segment
        for line in stock._skyline.lines:
            x = line.start.x
            y = line.start.y

            # Check if plate fits at this position
            if x + plate_width + spacing > stock.dimensions[0]:
                continue  # Doesn't fit horizontally
            if y + plate_height + spacing > stock.dimensions[1]:
                continue  # Doesn't fit vertically

            # Calculate waste (height difference to next skyline segment)
            waste = PlateNester._calculate_skyline_waste(stock._skyline, x, plate_width, y)

            # Create test position
            test_position = Point(x, y, 0)

            # Create test rectangle polygon for validation
            test_rect = Polygon([Point(x, y, 0), Point(x + plate_width, y, 0), Point(x + plate_width, y + plate_height, 0), Point(x, y + plate_height, 0)])

            # Check if this rectangle fits in remaining boundary
            if is_polygon_in_polygon_xy(test_rect, stock._remaining_boundary):
                if waste < best_waste:
                    best_position = test_position
                    best_waste = waste

        return best_position, best_waste

    @staticmethod
    def _calculate_skyline_waste(skyline, x, width, base_y):
        # Calculate the wasted vertical space when placing a plate.
        # This is the sum of height differences in the covered skyline region.

        waste = 0
        covered_width = 0

        for line in skyline.lines:
            segment_x = line.start.x
            segment_y = line.start.y
            segment_width = line.length

            # Check if this segment is in the covered region
            if segment_x >= x + width:
                break  # Past the covered region

            if segment_x + segment_width <= x:
                continue  # Before the covered region

            # This segment overlaps with the placement region
            overlap_start = max(segment_x, x)
            overlap_end = min(segment_x + segment_width, x + width)
            overlap_width = overlap_end - overlap_start

            # Add height difference as waste
            height_diff = abs(segment_y - base_y)
            waste += height_diff * overlap_width
            covered_width += overlap_width

        return waste

    @staticmethod
    def _update_skyline(stock, position, plate_width, plate_height):
        # Update the skyline profile after placing a plate.
        x = position.x
        new_y = position.y + plate_height

        # Build new skyline points
        new_points = []

        for line in stock._skyline.lines:
            segment_x = line.start.x
            segment_y = line.start.y
            segment_width = line.length
            segment_end_x = segment_x + segment_width

            # Segment is completely before the plate
            if segment_end_x <= x:
                if not new_points or new_points[-1] != [segment_x, segment_y, 0]:
                    new_points.append([segment_x, segment_y, 0])
                new_points.append([segment_end_x, segment_y, 0])
                continue

            # Segment is completely after the plate
            if segment_x >= x + plate_width:
                if not new_points or new_points[-1] != [segment_x, segment_y, 0]:
                    new_points.append([segment_x, segment_y, 0])
                new_points.append([segment_end_x, segment_y, 0])
                continue

            # Segment overlaps with the plate - split it
            # Left part (before plate)
            if segment_x < x:
                if not new_points or new_points[-1] != [segment_x, segment_y, 0]:
                    new_points.append([segment_x, segment_y, 0])
                new_points.append([x, segment_y, 0])

            # Middle part (covered by plate)
            if not new_points or new_points[-1][1] != new_y or new_points[-1][0] != x:
                # Add vertical step if needed
                if new_points and new_points[-1][0] == x and new_points[-1][1] != new_y:
                    new_points.append([x, new_y, 0])
                elif not new_points or new_points[-1][0] != x:
                    new_points.append([x, new_y, 0])
            new_points.append([x + plate_width, new_y, 0])

            # Right part (after plate)
            if segment_end_x > x + plate_width:
                # Add vertical step down if needed
                if segment_y != new_y:
                    new_points.append([x + plate_width, segment_y, 0])
                new_points.append([segment_end_x, segment_y, 0])

        # Remove duplicate consecutive points
        cleaned_points = []
        for pt in new_points:
            if not cleaned_points or cleaned_points[-1] != pt:
                cleaned_points.append(pt)

        stock._skyline = Polyline(cleaned_points)

    @staticmethod
    def _optimized_bottomleft_nest(plates, stock, spacing=0.0):
        # Optimized algorithm using actual polygon geometry.
        # TODO: Implement bottom-left algorithm for 2D plate nesting.
        # TODO: Algorithm needs to find valid Transformation (position + rotation)
        # TODO: Then call stock.add_element(plate, transformation)
        # Placeholder implementation
        stocks = []
        for plate in plates:
            new_stock = PlateStock(stock.dimensions, stock.thickness, spacing=spacing)
            # TODO: Missing transformation parameter - should pass Transformation()
            new_stock.add_element(plate)
            stocks.append(new_stock)

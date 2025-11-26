from warnings import warn

from compas.data import Data
from compas.geometry import Frame
from compas.tolerance import TOL
from compas.tolerance import Tolerance


class Stock(Data):
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
    element_data : dict[str, dict]
        Dictionary mapping each element GUID to a dict containing at least:
            'frame': assigned position frame (Frame)
            'key': graphnode key (int)


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
    element_data : dict[str, dict]
        Dictionary mapping each element GUID to a dict containing at least:
            'frame': assigned position frame (Frame)
            'key': graphnode key (int)
    """

    def __init__(self, length, width, height, spacing=0.0, element_data=None):
        super(Stock, self).__init__()
        self.length = length
        self.width = width
        self.height = height
        self.spacing = spacing
        self.element_data = element_data or {}  # {guid: {"frame": Frame, "key": int}}

    @property
    def __data__(self):
        return {
            "spacing": self.spacing,
            "element_data": self.element_data,
        }

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
        raise NotImplementedError("This method should be implemented in subclasses.")

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
        raise NotImplementedError("This method should be implemented in subclasses.")

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
        raise NotImplementedError("This method should be implemented in subclasses.")


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
    element_data : dict[str, dict], optional
        Dictionary mapping element GUIDs to a dict with:
            'frame': assigned position frame (Frame)
            'length': element length (float)
            'key': graphnode key
    blank_extension_transformation : :class:`~compas.geometry.Transformation`, optional
        Transformation to apply for blank extension positioning.


    Attributes
    ----------
    length : float
        Length of the stock piece.
    cross_section : tuple of float
        Cross-section dimensions sorted in ascending order for consistent comparison.
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, dict]
        Dictionary mapping element GUIDs to a dict with:
            'frame': assigned position frame (Frame)
            'key': graphnode key (int)
            'length': element length (float)
    blank_extension_transformation : :class:`~compas.geometry.Transformation` or None
        Transformation to apply for blank extension positioning.
    """

    def __init__(self, length, cross_section, spacing=0.0, element_data=None, blank_extension_transformation=None):
        # Validate cross_section before passing to parent constructor
        if not isinstance(cross_section, (list, tuple)) or len(cross_section) != 2:
            raise ValueError("cross_section must be a tuple or list of 2 dimensions")
        super(BeamStock, self).__init__(length=length, width=cross_section[0], height=cross_section[1], spacing=spacing, element_data=element_data)
        self.cross_section = tuple(cross_section)
        self._current_x_position = 0.0  # Track current position along length for placing beams
        self.blank_extension_transformation = blank_extension_transformation

    @property
    def __data__(self):
        data = super(BeamStock, self).__data__
        data["cross_section"] = self.cross_section
        data["length"] = self.length
        data["blank_extension_transformation"] = self.blank_extension_transformation
        return data

    @property
    def _remaining_length(self):
        # Get remaining unused length of the stock piece.
        return self.length - self._current_x_position

    @property
    def consoles_positions(self):
        """Get positions of consoles in the stock based on assigned beams."""
        return self._consoles_positions

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
        # Store element data with frame, blank length and graphnode key
        self.element_data[str(beam.guid)] = {
            "frame": position_frame,
            "key": beam.graphnode,
            "length": beam.blank_length,
        }

    def _get_position_frame(self, beam):
        # Get the position frame for a beam that is being added to this stock.
        # Orientation is based on the beam's cross-section relative to the stock's.
        # beam_cross_section = tuple([beam.width, beam.height])
        # # scenario where beam cross-section matches stock exactly (same width and height, same orientation)
        # if TOL.is_close(self.width, beam.width) and TOL.is_close(self.height, beam.height):
        position_frame = Frame.worldXY()
        # # scenario where beam cross-section values are the same but orientation is rotated 90 degrees
        # else:
        #     position_frame = Frame([0, 0, 0], [1, 0, 0], [0, 0, 1])
        #     position_frame.point.y = self.height  # offset in Y by stock height
        position_frame.point.x = self._current_x_position
        return position_frame

    def set_consoles_positions(self, model, threshold: float = 100.0, step: float = 5.0):
            """Compute and store console positions per assigned beam."""

            from optimalpositioner import consoles_positions as _cp

            count = len(self.element_data) if isinstance(self.element_data, dict) else 0
            mapping = {}
            for guid, data in (self.element_data or {}).items():
                key = data.get("key")
                beam_obj = None
                for b in model.beams or []:
                    if getattr(b, 'graphnode', None) == key or getattr(b, 'key', None) == key:
                        beam_obj = b
                        break
                if beam_obj is None:
                    continue
                positions = _cp(beam_obj, threshold=threshold, step=step, beams_on_stock=count)
                mapping[guid] = positions

            self._consoles_positions = mapping

            for guid, positions in mapping.items():
                key = str(guid)
                ed = self.element_data.get(key) or self.element_data.get(guid)
                if ed is None:
                    self.element_data[key] = {"console_positions": positions}
                    continue
                if isinstance(ed, dict):
                    new_ed = {}
                    inserted = False
                    for k, v in ed.items():
                        if k == 'console_positions':
                            continue
                        new_ed[k] = v
                        if k == 'length':
                            new_ed['console_positions'] = positions
                            inserted = True
                    if not inserted:
                        new_ed['console_positions'] = positions
                    self.element_data[key] = new_ed
                else:
                    self.element_data[key] = {"console_positions": positions}

            return mapping

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
    element_data : dict[str, dict]
        Dictionary mapping each element GUID to a dict containing at least:
            'frame': assigned position frame (Frame)
            'key': graphnode key (int)


    Attributes
    ----------
    dimensions : tuple of float
        Dimensions of the stock piece (length, width).
    thickness : float
        Thickness of the stock piece
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.).
    element_data : dict[str, dict]
        Dictionary mapping each element GUID to a dict containing at least:
            'frame': assigned position frame (Frame)
            'key': graphnode key (int)

    """

    def __init__(self, dimensions, thickness, spacing=0.0, element_data=None):
        # Validate dimensions before passing to parent constructor
        if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 2:
            raise ValueError("dimensions must be a tuple or list of 2 dimensions")
        super(PlateStock, self).__init__(length=dimensions[0], width=dimensions[1], height=thickness, spacing=spacing, element_data=element_data)
        self.dimensions = tuple(dimensions)
        self.thickness = thickness

    @property
    def __data__(self):
        data = super(PlateStock, self).__data__
        data["dimensions"] = self.dimensions
        data["thickness"] = self.thickness
        return data


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
    total_material_volume : float
        Total material volume across all stocks in cubic millimeters
    total_stock_pieces : dict
        Detailed report of stock pieces needed with their dimensions
    summary : str
        Human-readable summary of the nesting result
    """

    def __init__(self, stocks, tolerance=None):
        super(NestingResult, self).__init__()
        self.stocks = stocks if isinstance(stocks, list) else [stocks]
        self._tolerance = tolerance or Tolerance(unit="MM")

    @property
    def tolerance(self):
        return self._tolerance

    @tolerance.setter
    def tolerance(self, tolerance):
        if tolerance.unit == "MM":
            tolerance = Tolerance(unit="MM", precision=1)  # Ensure MM has at least 1 decimal place
        self._tolerance = tolerance

    @property
    def __data__(self):
        return {"stocks": self.stocks, "tolerance": self.tolerance}

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
                consoles_positions = []
                for data in stock.element_data.values():
                    key = data.get("key", None)
                    length = data.get("length", None)
                    beam_keys.append(key)
                    lengths.append(round(length, self.tolerance.precision))
                    consoles_positions.append(data.get("console_positions", None))
                waste = stock.length - sum(lengths) if lengths else stock.length
                valid_console_positions = [cp for cp in consoles_positions if cp is not None]
                # Formatted output
                lines.append(f"BeamKeys: {beam_keys}")
                lines.append(f"BeamLengths({self.tolerance.unit}): {lengths}")
                lines.append("Waste({}): {:.{prec}f}".format(self.tolerance.unit, waste, prec=self.tolerance.precision))
                lines.append("Spacing({}): {:.{prec}f}".format(self.tolerance.unit, float(stock.spacing), prec=self.tolerance.precision))
                if valid_console_positions:
                    lines.append(f"ConsolePositions({self.tolerance.unit}): {valid_console_positions}")
                lines.append("--------")
            else:
                raise NotImplementedError("Formatted summary not implemented for this stock type yet.")
        return "\n".join(lines)


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

    def nest(self, fast=True, consoles=False):
        """
        Perform 1D nesting of all beams in the model.

        Parameters
        ----------
        fast : bool, optional
            Whether to use a fast nesting algorithm (First Fit Decreasing) or a more
            accurate one (Best Fit Decreasing). Default is True (fast).
        consoles : bool, optional
            Whether to consider console positions in the nesting process. Default is False.
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

        # Populate consoles positions on each stock now that assignments are done
        for stock in nesting_stocks:
            if consoles:
                stock.set_consoles_positions(self.model)

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
                new_stock = BeamStock(stock.length, stock.cross_section, spacing=spacing, blank_extension_transformation=beam.attributes["blank_extension_transformation"])
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
                new_stock = BeamStock(stock.length, stock.cross_section, spacing=spacing, blank_extension_transformation=beam.attributes["blank_extension_transformation"])
                new_stock.add_element(beam)
                stocks.append(new_stock)

        return stocks

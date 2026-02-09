from warnings import warn

from compas.data import Data
from compas.geometry import Frame
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
        self._tolerance = tolerance or TOL

    @property
    def tolerance(self):
        return self._tolerance

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

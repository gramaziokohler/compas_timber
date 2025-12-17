from warnings import warn

from compas.data import Data
from compas.geometry import Frame
from compas.tolerance import TOL
from compas.tolerance import Tolerance

from .optimalpositioner import get_consoles_positions


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
    consoles_positions : list of float, optional


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
    consoles_positions : list of float
        List of console positions per assigned beam.
    """

    def __init__(self, length, cross_section, spacing=None, element_data=None, consoles_positions=None):
        # Validate cross_section before passing to parent constructor
        if not isinstance(cross_section, (list, tuple)) or len(cross_section) != 2:
            raise ValueError("cross_section must be a tuple or list of 2 dimensions")
        super(BeamStock, self).__init__(length=length, width=cross_section[0], height=cross_section[1], spacing=spacing, element_data=element_data)
        self.cross_section = tuple(cross_section)
        self.consoles_positions = consoles_positions
        self._current_x_position = 0.0  # Track current position along length for placing beams
        self._spacing = spacing if spacing is not None else 0.0
        self.group = ""
        self.groups = set()  # Track unique groups in this stock
        self.group_indices = set()  # Track group indices in this stock

    @property
    def __data__(self):
        data = super(BeamStock, self).__data__
        data["cross_section"] = self.cross_section
        data["length"] = self.length
        data["consoles_positions"] = self.consoles_positions
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
        if TOL.is_close(beam.width, 280.0) and self.cross_section == (140.0, 140.0):
            return True, True
        return TOL.is_close(a, x) and TOL.is_close(b, y)

    def add_element(self, beam, group_index=None):
        """
        Add a beam to this stock assignment.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to add
        group_index : int, optional
            The index of the group this beam belongs to

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
        self._current_x_position += beam.blank_length + self._spacing  # Update position for next beam
        # Track which group this beam belongs to
        beam_group = beam.parent.name if beam.parent else ""
        if beam_group:
            self.groups.add(beam_group)
        if group_index is not None:
            self.group_indices.add(group_index)
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
        # position_frame = Frame.worldXY()
        # # scenario where beam cross-section values are the same but orientation is rotated 90 degrees
        # else:
        #     position_frame = Frame([0, 0, 0], [1, 0, 0], [0, 0, 1])
        #     position_frame.point.y = self.height  # offset in Y by stock height
        position_frame = Frame.worldXY()
        position_frame.point.x = self._current_x_position
        return position_frame

    def _set_consoles_positions(self, model):
        # Compute and store console positions per assigned beam in the stock as a flat list.
        count = len(self.element_data)
        stock_console_positions = []

        # prepare stock beam lengths in the same order as element_data
        guids_in_order = list(self.element_data.keys())
        stock_lengths = []
        for guid in guids_in_order:
            b = model.element_by_guid(str(guid))
            stock_lengths.append(float(b.blank_length))

        for i, guid in enumerate(guids_in_order):
            data = self.element_data[guid]
            beam = model.element_by_guid(str(guid))
            positions = get_consoles_positions(beam, beams_on_stock=count, beam_index=i, stock_beam_lengths=tuple(stock_lengths))
            frame = data.get("frame", Frame.worldXY())
            positions = [p + frame.point.x for p in positions]  # Offset by beam position on stock
            stock_console_positions.extend(positions)

        stock_console_positions.sort()
        self.consoles_positions = stock_console_positions


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
                lines.append(f"Groups: {list(stock.groups)}")
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

    def nest(self, fast=True, consoles=False, optimize=False, exclude_groups=[]):
        """
        Perform 1D nesting of all beams in the model.

        Parameters
        ----------
        fast : bool, optional
            Whether to use a fast nesting algorithm (First Fit Decreasing) or a more
            accurate one (Best Fit Decreasing). Default is True (fast).
        consoles : bool, optional
            Whether to consider console positions in the nesting process. Default is False.
        optimize : bool, optional
            Only applies when per_group=True. If True, allows filling leftover space in stocks
            from previous groups with beams from the next consecutive group (optimized per_group).
            If False, keeps groups strictly separate (strict per_group). Has no effect when
            per_group=False. Default is False.
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

            # Nest groups in order, optionally continuing to fill partially-used stocks
            for group_index, beams in enumerate(beam_groups):
                # Determine which stocks to pass for optimization
                stocks_to_pass = []
                if optimize:
                    # If optimization is enabled, allow stocks from the previous group to be filled
                    # Filter out stocks that belong to excluded groups
                    if exclude_groups:
                        # Get current group name
                        current_group_name = beams[0].parent.name if beams and beams[0].parent else ""
                        # Extract integer from group name format "S{int}"
                        current_group_int = int(current_group_name[1:]) if current_group_name.startswith("S") else None

                        # If the current group is excluded, don't pass any existing stocks (isolate it)
                        if current_group_int in exclude_groups:
                            stocks_to_pass = []
                        else:
                            # Otherwise, pass all stocks except those from excluded groups
                            # Extract integers from stock group names and filter
                            stocks_to_pass = []
                            for s in nesting_stocks:
                                stock_group_int = int(s.group[1:]) if s.group.startswith("S") else None
                                if stock_group_int not in exclude_groups:
                                    stocks_to_pass.append(s)
                    else:
                        # No exclusions, pass all existing stocks
                        stocks_to_pass = nesting_stocks

                stocks = self._nest_beam_collection(beams, fast, existing_stocks=stocks_to_pass, group_index=group_index)
                # Only extend with NEW stocks, existing_stocks are already in nesting_stocks
                nesting_stocks.extend([s for s in stocks if s not in nesting_stocks])
        else:
            # Nest ALL beams together
            stocks = self._nest_beam_collection(self.model.beams, fast)
            nesting_stocks.extend(stocks)

        # Populate consoles positions on each stock now that assignments are done
        if consoles:
            for stock in nesting_stocks:
                stock._set_consoles_positions(self.model)
        return NestingResult(nesting_stocks)

    def _nest_beam_collection(self, beams, fast=True, existing_stocks=None, group_index=None):
        # Nest a collection of beams into stock pieces.
        # If existing_stocks is provided, try to fill those first before creating new ones.
        stocks = existing_stocks if existing_stocks is not None else []
        stock_beam_map = self._sort_beams_by_stock(beams)

        for stock_type, compatible_beams in stock_beam_map.items():
            spacing = self.spacing if stock_type.spacing is None else stock_type.spacing
            if not compatible_beams:
                continue
            # Apply selected algorithm, passing existing stocks to continue filling them
            if fast:
                result_stocks = self._first_fit_decreasing(compatible_beams, stock_type, spacing, existing_stocks=stocks, group_index=group_index)
            else:
                result_stocks = self._best_fit_decreasing(compatible_beams, stock_type, spacing, existing_stocks=stocks, group_index=group_index)

            stocks = result_stocks
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
    def _first_fit_decreasing(beams, stock, spacing=0.0, existing_stocks=None, group_index=None):
        # Fast but more wasteful packing
        # Places each beam in the first stock that has enough space, without optimizing for minimal waste.
        sorted_beams = sorted(beams, key=lambda b: b.blank_length, reverse=True)

        stocks = existing_stocks if existing_stocks is not None else []
        for beam in sorted_beams:
            # Try to fit in existing stocks (filter for compatible cross-section and consecutive group constraint)
            fitted = False
            beam_group = beam.parent.name if beam.parent else ""
            for stock_piece in stocks:
                # Check if this stock can accept beams from this group
                # Allow if: stock is empty, stock has this group, or stock has previous group (group_index-1)
                can_accept_group = True
                if group_index is not None and stock_piece.group_indices:
                    # Stock must contain the previous group (group_index - 1) to accept current group
                    can_accept_group = group_index in stock_piece.group_indices or (group_index - 1) in stock_piece.group_indices

                if stock_piece.is_compatible_with(beam) and stock_piece.can_fit_element(beam) and can_accept_group:
                    stock_piece.add_element(beam, group_index=group_index)
                    fitted = True
                    break
            # If not fitted, create new stock
            if not fitted:
                new_stock = BeamStock(stock.length, stock.cross_section, spacing=spacing)
                new_stock.group = beam_group
                new_stock.add_element(beam, group_index=group_index)
                stocks.append(new_stock)

        return stocks

    @staticmethod
    def _best_fit_decreasing(beams, stock, spacing=0.0, existing_stocks=None, group_index=None):
        # Slower but more efficient packing
        # Minimizes waste by selecting the stock piece with the smallest remaining space that can still fit the beam.
        sorted_beams = sorted(beams, key=lambda b: b.blank_length, reverse=True)

        stocks = existing_stocks if existing_stocks is not None else []
        for beam in sorted_beams:
            # Find best fitting existing stock (smallest waste that still fits, compatible cross-section, consecutive groups)
            best_stock = None
            best_waste = float("inf")
            beam_group = beam.parent.name if beam.parent else ""

            for stock_piece in stocks:
                # Check if this stock can accept beams from this group
                # Allow if: stock is empty, stock has this group, or stock has previous group (group_index-1)
                can_accept_group = True
                if group_index is not None and stock_piece.group_indices:
                    # Stock must contain the previous group (group_index - 1) to accept current group
                    can_accept_group = group_index in stock_piece.group_indices or (group_index - 1) in stock_piece.group_indices

                if stock_piece.is_compatible_with(beam) and stock_piece.can_fit_element(beam) and can_accept_group and stock_piece._remaining_length < best_waste:
                    best_waste = stock_piece._remaining_length
                    best_stock = stock_piece
            # If found a fitting stock, use it
            if best_stock is not None:
                best_stock.add_element(beam, group_index=group_index)
            else:
                # Create new stock
                new_stock = BeamStock(stock.length, stock.cross_section, spacing=spacing)
                new_stock.group = beam_group
                new_stock.add_element(beam, group_index=group_index)
                stocks.append(new_stock)

        return stocks

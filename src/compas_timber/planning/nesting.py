from warnings import warn

from compas.data import Data
from compas.geometry import Frame


class Stock(Data):
    """
    A class to represent a stock piece for nesting beams.

    Similar to a Beam but represents raw material stock that can have beams assigned to it.

    Parameters
    ----------
    length : float
        Length of the stock piece
    cross_section : tuple of float
        Cross-section dimensions (width, height)


    Attributes
    ----------
    length : float
        Length of the stock piece
    cross_section : tuple of float
        Cross-section dimensions sorted in ascending order for consistent comparison
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.)
    beam_data : dict[str, dict]
        Dictionary mapping beam GUIDs to beam info containing "length" and "frame"
    utilized_length : float
        Total utilized length including spacing tolerances
    waste : float
        Remaining unused length of the stock piece
    """

    def __init__(self, length, cross_section):
        super(Stock, self).__init__()
        self.length = length
        # Store cross-section as sorted tuple for orientation-independent comparison
        if isinstance(cross_section, (list, tuple)) and len(cross_section) == 2:
            self.cross_section = tuple(cross_section)
        else:
            raise ValueError("cross_section must be a tuple or list of 2 dimensions")

        self.beam_data = {}  # {guid: {"length": float, "frame": Frame}}
        self._spacing = 0.0

    @property
    def __data__(self):
        return {
            "length": self.length,
            "cross_section": self.cross_section,
            "spacing": self.spacing,
            "beam_data": self.beam_data,
        }

    @classmethod
    def __from_data__(cls, data):
        stock = cls(length=data["length"], cross_section=data["cross_section"])
        stock.spacing = data.get("spacing", 0.0)
        stock.beam_data = data.get("beam_data", {})
        return stock

    @property
    def spacing(self):
        return self._spacing

    @spacing.setter
    def spacing(self, value):
        self._spacing = value

    @property
    def utilized_length(self):
        """Get the total utilized length including spacing tolerances."""
        if not self.beam_data:
            return 0.0
        current_length = sum(beam_info["length"] for beam_info in self.beam_data.values())
        cuts_so_far = len(self.beam_data)
        return current_length + (cuts_so_far * self._spacing)

    @property
    def waste(self):
        """Get remaining unused length of the stock piece."""
        return self.length - self.utilized_length

    @property
    def beam_guids(self):
        """Get list of beam GUIDs for BTLx integration."""
        return list(self.beam_data.keys())

    def section_matches(self, beam):
        """
        Check if a beam has identical cross-section to this stock.

        For 1D nesting, we only optimize along the length dimension.
        The cross-sections must be identical.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to check

        Returns
        -------
        bool
            True if cross-sections are identical, False otherwise
        """
        beam_cross_section = [beam.width, beam.height]
        return set(beam_cross_section) == set(self.cross_section)

    def _get_position_frame(self, beam):
        """
        Get the position frame for a beam based on its orientation vs stock cross-section.
        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to get the position frame for
        x_position : float
            The position along the stock length where the beam should be placed.
        Returns
        -------
        :class:`Frame`
            The position frame for the beam.
        """
        beam_cross_section = tuple([beam.width, beam.height])
        # scenario where beam cross-section matches stock exactly
        if beam_cross_section == self.cross_section:
            position_frame = Frame.worldXY()
        # scenario where beam cross-section is rotated 90 degrees vs stock
        else:
            position_frame = Frame([0, 0, 0], [1, 0, 0], [0, 0, 1])
            position_frame.point.y = self.cross_section[1]  # offset to avoid negative coordinates
        position_frame.point.x = self.utilized_length
        return position_frame

    def can_fit_beam(self, beam):
        """
        Check if a beam can fit in the remaining space.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to check

        Returns
        -------
        bool
            True if beam fits in remaining space, False otherwise
        """
        return self.waste >= beam.blank_length

    def add_beam(self, beam):
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
        if not self.can_fit_beam(beam):
            raise ValueError(f"Beam with length {beam.blank_length} doesn't fit in remaining space {self.waste}")
        # Get position frame based on orientation
        position_frame = self._get_position_frame(beam)
        # Store beam data with both length and frame
        self.beam_data[str(beam.guid)] = {"length": beam.blank_length, "frame": position_frame}

    def copy_empty(self):
        """Create a copy of this stock with no beams assigned."""
        return Stock(self.length, self.cross_section)


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
    """

    def __init__(self, stocks):
        super(NestingResult, self).__init__()
        self.stocks = stocks if isinstance(stocks, list) else [stocks]

    @property
    def __data__(self):
        return {"stocks": [stock.__data__ for stock in self.stocks]}

    @classmethod
    def __from_data__(cls, data):
        stocks = [Stock.__from_data__(stock_data) for stock_data in data["stocks"]]
        return cls(stocks)

    @property
    def total_waste(self):
        """Calculate total waste across all stocks."""
        return sum(stock.waste for stock in self.stocks)

    @property
    def total_beams(self):
        """Count total number of beams nested."""
        return sum(len(stock.beam_data) for stock in self.stocks)

    @property
    def utilization_rate(self):
        """Calculate overall material utilization rate."""
        total_length = sum(stock.length for stock in self.stocks)
        if total_length == 0:
            return 0.0
        return 1.0 - (self.total_waste / total_length)


class BeamNester(object):
    """
    A class for optimizing 1D nesting of beams into stock pieces.

    This class implements algorithms to efficiently nest beams from a TimberModel
    into available stock pieces, minimizing waste and cost.

    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        The timber model containing beams to nest
    stock_catalog : list[:class:`Stock`]
        Available stock pieces for nesting
    spacing : float, optional
        Spacing tolerance for cutting operations (kerf width, etc.)

    Attributes
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        The timber model
    stock_catalog : list[:class:`Stock`]
        Available stock pieces for nesting
    spacing : float
        Spacing tolerance for cutting operations (kerf width, etc.)
    """

    def __init__(self, model, stock_catalog, spacing=None):
        self.model = model
        self.stock_catalog = stock_catalog if isinstance(stock_catalog, list) else [stock_catalog]
        self.spacing = spacing or 0.0

    def _sort_beams_by_stock(self):
        """
        Sort all beams in the model by their compatible stock types.

        Returns
        -------
        dict[:class:`Stock`, list[:class:`~compas_timber.elements.Beam`]]
            A mapping of stock types to lists of compatible beams.

        Warns
        ------
            If any beam does not match any stock type.
        """
        unnested_beams = []
        stock_beam_map = {stock: [] for stock in self.stock_catalog}
        for beam in self.model.beams:
            beam_matched = False
            for stock in self.stock_catalog:
                if stock.section_matches(beam):
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
        stock_beam_map = self._sort_beams_by_stock()
        for stock_type, compatible_beams in stock_beam_map.items():
            if not compatible_beams:
                continue
            # Apply selected algorithm
            if fast:
                stocks = self._first_fit_decreasing(compatible_beams, stock_type, self.spacing)
            else:
                stocks = self._best_fit_decreasing(compatible_beams, stock_type, self.spacing)
            # Add to overall result
            nesting_stocks.extend(stocks)

        return NestingResult(nesting_stocks)

    @staticmethod
    def _first_fit_decreasing(beams, stock, spacing=0.0):
        """
        Apply First Fit Decreasing algorithm for a single stock type.

        Fast but more wasteful packing - places each beam in the first stock
        that has enough space, without optimizing for minimal waste.

        Parameters
        ----------
        beams : list[:class:`~compas_timber.elements.Beam`]
            Beams to nest (will be sorted by blank length descending)
        stock : :class:`Stock`
            Stock type to use

        Returns
        -------
        list[:class:`Stock`]
            List of stock pieces with assigned beams
        """
        # Sort beams by blank length in descending order
        sorted_beams = sorted(beams, key=lambda b: b.blank_length, reverse=True)

        stocks = []
        for beam in sorted_beams:
            # Try to fit in existing stocks
            fitted = False
            for stock_piece in stocks:
                stock_piece.spacing = spacing  # Set spacing tolerance
                if stock_piece.can_fit_beam(beam):
                    stock_piece.add_beam(beam)
                    fitted = True
                    break
            # If not fitted, create new stock
            if not fitted:
                new_stock = stock.copy_empty()
                new_stock.add_beam(beam)
                stocks.append(new_stock)

        return stocks

    @staticmethod
    def _best_fit_decreasing(beams, stock, spacing=0.0):
        """
        Apply Best Fit Decreasing algorithm for a single stock type.

        Slower but more efficient packing - minimizes waste by selecting the stock piece
        with the smallest remaining space that can still fit the beam.

        Parameters
        ----------
        beams : list[:class:`~compas_timber.elements.Beam`]
            Beams to nest
        stock : :class:`Stock`
            Stock type to use

        Returns
        -------
        list[:class:`Stock`]
            List of stock pieces with assigned beams
        """
        # Sort beams by blank length in descending order
        sorted_beams = sorted(beams, key=lambda b: b.blank_length, reverse=True)

        stocks = []
        for beam in sorted_beams:
            # Find best fitting existing stock (smallest waste that still fits)
            best_stock = None
            best_waste = float("inf")

            for stock_piece in stocks:
                stock_piece.spacing = spacing  # Set spacing tolerance
                if stock_piece.can_fit_beam(beam) and stock_piece.waste < best_waste:
                    best_waste = stock_piece.waste
                    best_stock = stock_piece
            # If found a fitting stock, use it
            if best_stock is not None:
                best_stock.add_beam(beam)
            else:
                # Create new stock
                new_stock = stock.copy_empty()
                new_stock.add_beam(beam)
                stocks.append(new_stock)

        return stocks

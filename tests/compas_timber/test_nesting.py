import pytest
import warnings

from compas.geometry import Frame

from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.planning import Stock
from compas_timber.planning import BeamNester
from compas_timber.planning import NestingResult

# ============================================================================
# Stock Tests
# ============================================================================


def test_initialization_and_basic_properties():
    """Test Stock initialization with valid parameters and basic property access."""
    stock = Stock(6000, (120, 60))

    assert stock.length == 6000
    assert stock.cross_section == (60, 120)  # Should be sorted
    assert stock.cutting_tolerance == 0.0  # Default value if not set
    assert stock.beam_data == {}
    assert stock.waste == 6000  # Full length when empty


def test_cross_section_normalization():
    """Test that cross-sections are normalized to sorted tuples."""
    # Test orientation independence
    stock1 = Stock(6000, (120, 60))
    stock2 = Stock(6000, [60, 120])  # Different order, list input

    assert stock1.cross_section == (60, 120)
    assert stock2.cross_section == (60, 120)
    assert stock1.cross_section == stock2.cross_section


def test_section_matching():
    """Test beam cross-section matching logic."""
    stock = Stock(6000, (60, 120))
    # Test exact match
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=60, height=120)
    assert stock.section_matches(beam1)

    # Test orientation independence
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    assert stock.section_matches(beam2)

    # Test square cross-section
    square_stock = Stock(6000, (100, 100))
    beam3 = Beam(frame=Frame.worldXY(), length=2000, width=100, height=100)
    assert square_stock.section_matches(beam3)

    # Test non-matching cross-section
    beam4 = Beam(frame=Frame.worldXY(), length=2000, width=80, height=160)
    assert not stock.section_matches(beam4)


def test_beam_addition_and_capacity_tracking():
    """Test adding beams and tracking used length/waste."""
    stock = Stock(6000, (60, 120))
    stock.cutting_tolerance = 1.0

    # Add first beam
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=60, height=120)
    stock.add_beam(beam1)
    expected_waste1 = stock.length - beam1.blank_length

    assert len(stock.beam_data) == 1
    assert beam1.guid in stock.beam_data
    assert stock.beam_data[beam1.guid] == 2000
    assert stock.waste == expected_waste1

    # Add second beam
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=60, height=120)
    stock.add_beam(beam2)
    expected_waste2 = expected_waste1 - beam2.blank_length - stock.cutting_tolerance

    assert len(stock.beam_data) == 2
    assert beam2.guid in stock.beam_data
    assert stock.beam_data[beam2.guid] == 1500
    assert stock.waste == expected_waste2


def test_beam_fitting_validation():
    """Test beam fitting validation and error handling."""
    stock = Stock(6000, (60, 120))
    cutting_tolerance = 1.0
    stock.cutting_tolerance = cutting_tolerance

    # Test beam that fits
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=60, height=120)
    assert stock.can_fit_beam(beam1)

    # Add the beam
    stock.add_beam(beam1)
    assert stock.waste == 4000

    # Test beam that exactly fits remaining space
    beam2 = Beam(frame=Frame.worldXY(), length=4000 - cutting_tolerance, width=60, height=120)
    assert stock.can_fit_beam(beam2)

    # Add the beam
    stock.add_beam(beam2)
    assert stock.waste == 0

    # Test beam that doesn't fit
    beam3 = Beam(frame=Frame.worldXY(), length=1000, width=60, height=120)
    assert not stock.can_fit_beam(beam3)


def test_serialization():
    """Test data serialization and copy functionality."""
    # Create stock with beams
    stock = Stock(6000, (60, 120))
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=60, height=120)
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=60, height=120)
    stock.add_beam(beam1)
    stock.add_beam(beam2)

    # Set cutting_tolerance
    stock.cutting_tolerance = 5.0

    # Test serialization
    data = stock.__data__
    expected_data = {"length": 6000, "cross_section": (60, 120), "cutting_tolerance": 5.0, "beam_data": {beam1.guid: 2000, beam2.guid: 1500}}

    assert data == expected_data

    # Test deserialization
    restored_stock = Stock.__from_data__(data)
    assert restored_stock.length == stock.length
    assert restored_stock.cross_section == stock.cross_section
    assert restored_stock.cutting_tolerance == stock.cutting_tolerance
    assert restored_stock.beam_data == stock.beam_data


def test_copy_empty():
    """Test data serialization and copy functionality."""
    # Create stock with beams
    stock = Stock(6000, (60, 120))
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=60, height=120)
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=60, height=120)
    stock.add_beam(beam1)
    stock.add_beam(beam2)
    stock.cutting_tolerance = 5.0

    assert stock.cutting_tolerance == 5.0
    assert stock.beam_data == {beam1.guid: 2000, beam2.guid: 1500}
    assert stock.waste == 2500 - 5.0

    # Test copy_empty
    empty_copy = stock.copy_empty()
    assert empty_copy.length == stock.length
    assert empty_copy.cross_section == stock.cross_section
    assert empty_copy.cutting_tolerance == 0.0  # Default value
    assert empty_copy.beam_data == {}  # Should be empty
    assert empty_copy.waste == 6000  # Full capacity


# ============================================================================
# BeamNester Tests
# ============================================================================


def test_beam_nester_initialization():
    """Test BeamNester initialization with valid parameters."""
    model = TimberModel()
    stock_catalog = [
        Stock(6000, (120, 60)),
        Stock(5000, (80, 40)),
    ]

    nester = BeamNester(model, stock_catalog, cutting_tolerance=5.0)

    assert nester.model is model
    assert nester.stock_catalog == stock_catalog
    assert nester.cutting_tolerance == 5.0


def test_beam_nester_single_stock_initialization():
    """Test BeamNester initialization with single stock (not list)."""
    model = TimberModel()
    stock = Stock(6000, (120, 60))

    nester = BeamNester(model, stock, 3.0)

    assert nester.model is model
    assert nester.stock_catalog == [stock]  # Should be converted to list
    assert nester.cutting_tolerance == 3.0


def test_sort_beams_by_stock():
    """Test the sort_beams_by_stock method."""
    model = TimberModel()

    # Add compatible and incompatible beams
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)  # Compatible
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=200, height=100)  # Incompatible
    beam3 = Beam(frame=Frame.worldXY(), length=1000, width=120, height=60)  # Compatible

    model.add_element(beam1)
    model.add_element(beam2)
    model.add_element(beam3)

    stock_catalog = [Stock(6000, (120, 60))]
    nester = BeamNester(model, stock_catalog)

    # Test sorting with warning capture
    with pytest.warns(UserWarning, match="Found 1 beam\\(s\\) incompatible.*200x100mm"):
        stock_beam_map = nester.sort_beams_by_stock()

    # Check that compatible beams were sorted correctly
    compatible_beams = stock_beam_map[stock_catalog[0]]
    assert len(compatible_beams) == 2
    assert beam1 in compatible_beams
    assert beam3 in compatible_beams
    assert beam2 not in compatible_beams


def test_first_fit_decreasing_single_stock():
    """Test First Fit Decreasing algorithm for single stock type."""
    # Create beams of different lengths
    beam1 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam3 = Beam(frame=Frame.worldXY(), length=1500, width=120, height=60)
    beam4 = Beam(frame=Frame.worldXY(), length=2500, width=120, height=60)

    beams = [beam1, beam2, beam3, beam4]
    stock = Stock(6000, (120, 60))

    result_stocks = BeamNester.first_fit_decreasing(beams, stock)

    # Should have 2 stocks: first with beam1+beam4 (5500), second with beam2+beam3 (3500)
    assert len(result_stocks) == 2

    # Check first stock - gets beam1 (3000) + beam4 (2500) = 5500
    assert len(result_stocks[0].beam_data) == 2
    assert beam1.guid in result_stocks[0].beam_data
    assert beam4.guid in result_stocks[0].beam_data
    assert result_stocks[0].waste == 500  # 6000 - 3000 - 2500

    # Check second stock - gets beam2 (2000) + beam3 (1500) = 3500
    assert len(result_stocks[1].beam_data) == 2
    assert beam2.guid in result_stocks[1].beam_data
    assert beam3.guid in result_stocks[1].beam_data
    assert result_stocks[1].waste == 2500  # 6000 - 2000 - 1500


def test_best_fit_decreasing_single_stock():
    """Test Best Fit Decreasing algorithm for single stock type."""
    # Create beams of specific lengths to test best fit behavior
    beam1 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam3 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)  # Should fit with beam1
    beam4 = Beam(frame=Frame.worldXY(), length=500, width=120, height=60)

    beams = [beam1, beam2, beam3, beam4]
    stock = Stock(6000, (120, 60))

    result_stocks = BeamNester.best_fit_decreasing(beams, stock)

    # Should have 2 stocks: first with beam1+beam3 (6000), second with beam2+beam4 (2500)
    assert len(result_stocks) == 2

    # Check first stock (beam1 + beam3)
    assert len(result_stocks[0].beam_data) == 2
    assert beam1.guid in result_stocks[0].beam_data
    assert beam3.guid in result_stocks[0].beam_data
    assert result_stocks[0].waste == 0  # 6000 - 3000 - 3000

    # Check second stock (beam2 + beam4)
    assert len(result_stocks[1].beam_data) == 2
    assert beam2.guid in result_stocks[1].beam_data
    assert beam4.guid in result_stocks[1].beam_data
    assert result_stocks[1].waste == 3500  # 6000 - 2000 - 500


def test_nest_beams_no_compatible_stock():
    """Test nesting when no stock matches beam cross-sections."""
    model = TimberModel()

    # Add beam with cross-section not in catalog
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=200, height=100)
    model.add_element(beam1)

    stock_catalog = [Stock(6000, (120, 60))]

    nester = BeamNester(model, stock_catalog)

    # Should warn about incompatible beam cross-section
    with pytest.warns(UserWarning, match="Found 1 beam\\(s\\) incompatible.*200x100mm"):
        nesting_result = nester.nest()

    # Should return empty list since no compatible stock
    assert len(nesting_result.stocks) == 0


def test_nest_beams_multiple_incompatible_cross_sections():
    """Test nesting with multiple different incompatible beam cross-sections."""
    model = TimberModel()

    # Add beams with different incompatible cross-sections
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=200, height=100)
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=150, height=80)
    beam3 = Beam(frame=Frame.worldXY(), length=1000, width=200, height=100)  # Same as beam1
    model.add_element(beam1)
    model.add_element(beam2)
    model.add_element(beam3)

    stock_catalog = [Stock(6000, (120, 60))]

    nester = BeamNester(model, stock_catalog)

    # Capture warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        nesting_result = nester.nest()

        # Should return empty list since no compatible stock
        assert len(nesting_result.stocks) == 0

        # Should have issued a warning with unique beam dimensions
        assert len(w) == 1
        assert issubclass(w[0].category, UserWarning)
        warning_message = str(w[0].message)
        assert "Found 3 beam(s) incompatible with available stock catalog" in warning_message
        # Should contain both unique cross-sections
        assert "200x100mm" in warning_message
        assert "150x80mm" in warning_message


def test_nest_beams_empty_model():
    """Test nesting with empty model (no beams)."""
    model = TimberModel()
    stock_catalog = [Stock(6000, (120, 60))]

    nester = BeamNester(model, stock_catalog)
    nesting_result = nester.nest()

    # Should return empty list since no beams to nest
    assert len(nesting_result.stocks) == 0


def test_nest_method_basic_functionality():
    """Test BeamNester.nest() method with basic nesting scenario."""
    model = TimberModel()

    # Add beams with compatible cross-sections
    beam1 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam3 = Beam(frame=Frame.worldXY(), length=1000, width=120, height=60)

    model.add_element(beam1)
    model.add_element(beam2)
    model.add_element(beam3)

    stock_catalog = Stock(6000, (120, 60))
    nester = BeamNester(model, stock_catalog)

    # Test nest() method
    nesting_result = nester.nest()

    # Should return NestingResult instance
    assert isinstance(nesting_result, NestingResult)
    assert len(nesting_result.stocks) == 1  # All beams should fit in one stock

    # Check that all beams are assigned
    all_beam_guids = set()
    for stock in nesting_result.stocks:
        all_beam_guids.update(stock.beam_guids)

    expected_guids = {beam1.guid, beam2.guid, beam3.guid}
    assert all_beam_guids == expected_guids


def test_nest_method_with_incompatible_beams():
    """Test BeamNester.nest() method with incompatible beams."""
    model = TimberModel()

    # Add compatible and incompatible beams
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)  # Compatible
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=200, height=100)  # Incompatible

    model.add_element(beam1)
    model.add_element(beam2)

    stock_catalog = [Stock(6000, (120, 60))]
    nester = BeamNester(model, stock_catalog)

    # Should warn about incompatible beam
    with pytest.warns(UserWarning, match="Found 1 beam\\(s\\) incompatible.*200x100mm"):
        nesting_result = nester.nest()

    # Should have one stock with only the compatible beam
    assert isinstance(nesting_result, NestingResult)
    assert len(nesting_result.stocks) == 1
    assert beam1.guid in nesting_result.stocks[0].beam_data
    assert beam2.guid not in nesting_result.stocks[0].beam_data


# ============================================================================
# NestingResult Tests
# ============================================================================


def test_nesting_result_basic_properties():
    """Test NestingResult basic properties and functionality."""
    # Create some test stocks with beams
    stock1 = Stock(6000, (120, 60))
    stock2 = Stock(6000, (120, 60))

    beam1 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)

    stock1.add_beam(beam1)
    stock2.add_beam(beam2)

    stocks = [stock1, stock2]
    result = NestingResult(stocks)

    # Test basic properties
    assert result.stocks == stocks
    assert len(result.stocks) == 2
    assert result.total_waste == stock1.waste + stock2.waste
    assert result.total_beams == 2
    assert result.utilization_rate == pytest.approx((3000 + 2000) / (2 * 6000))


def test_nesting_result_serialization():
    """Test NestingResult serialization functionality."""
    # Create test stock with beam
    stock = Stock(6000, (120, 60))
    beam = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    stock.add_beam(beam)

    result = NestingResult(stock)

    # Test serialization
    data = result.__data__
    assert len(data["stocks"]) == 1

    # Test deserialization
    restored_result = NestingResult.__from_data__(data)
    assert len(restored_result.stocks) == 1
    assert restored_result.stocks[0].length == stock.length
    assert restored_result.stocks[0].cross_section == stock.cross_section
    assert restored_result.total_waste == result.total_waste
    assert restored_result.total_beams == result.total_beams
    assert restored_result.utilization_rate == result.utilization_rate

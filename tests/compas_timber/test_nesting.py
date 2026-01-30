import pytest
import warnings

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Polyline

from compas_timber.elements import Beam
from compas_timber.elements import Panel
from compas_timber.model import TimberModel
from compas_timber.planning import BeamStock
from compas_timber.planning import BeamNester
from compas_timber.planning import NestedElementData
from compas_timber.planning import NestingResult

# ============================================================================
# BeamStock Tests
# ============================================================================


def test_initialization_and_basic_properties_tuple():
    """Test BeamStock initialization with valid parameters and basic property access."""
    stock = BeamStock(6000, (120, 60))

    assert stock.length == 6000
    assert stock.cross_section == (120, 60)

    assert stock.spacing == 0.0  # Default value if not set
    assert stock.element_data == {}
    assert stock._current_x_position == 0.0  # Nothing utilized when empty


def test_initialization_and_basic_properties_list():
    """Test BeamStock initialization with list cross-section input."""
    stock = BeamStock(6000, [120, 60])  # List input

    assert stock.length == 6000
    assert stock.cross_section == (120, 60)

    assert stock.spacing == 0.0  # Default value if not set
    assert stock.element_data == {}
    assert stock._current_x_position == 0.0  # Nothing utilized when empty


def test_is_compatible_with():
    """Test beam cross-section matching logic."""
    stock = BeamStock(6000, (60, 120))
    # Test exact match
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=60, height=120)
    assert stock.is_compatible_with(beam1)

    # Test orientation independence (both should match due to sorted comparison)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    assert stock.is_compatible_with(beam2)

    # Test square cross-section
    square_stock = BeamStock(6000, (100, 100))
    beam3 = Beam(frame=Frame.worldXY(), length=2000, width=100, height=100)
    assert square_stock.is_compatible_with(beam3)

    # Test non-matching cross-section
    beam4 = Beam(frame=Frame.worldXY(), length=2000, width=80, height=160)
    assert not stock.is_compatible_with(beam4)


def test_beam_addition_and_capacity_tracking():
    """Test adding beams and tracking used length/waste."""
    stock = BeamStock(6000, (60, 120))
    stock.spacing = 1.0

    # Add first beam
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=60, height=120)
    stock.add_element(beam1)

    expected_x_position1 = beam1.blank_length + stock.spacing
    expected_frame1 = Frame.worldXY()
    element_info = stock.element_data[str(beam1.guid)]

    assert len(stock.element_data) == 1
    assert str(beam1.guid) in stock.element_data
    assert isinstance(element_info, NestedElementData)
    assert element_info.frame == expected_frame1
    assert element_info.key == beam1.name + "-" + str(beam1.guid)[:4]
    assert element_info.length == beam1.blank_length
    assert stock._current_x_position == expected_x_position1

    # Add second beam
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=60, height=120)
    stock.add_element(beam2)

    expected_frame2 = Frame.worldXY()
    expected_frame2.point.x = expected_x_position1
    expected_x_position2 = expected_x_position1 + beam2.blank_length + stock.spacing
    element_info = stock.element_data[str(beam2.guid)]

    assert len(stock.element_data) == 2
    assert str(beam2.guid) in stock.element_data
    assert isinstance(element_info, NestedElementData)
    assert element_info.frame == expected_frame2
    assert element_info.key == beam2.name + "-" + str(beam2.guid)[:4]
    assert element_info.length == beam2.blank_length
    assert stock._current_x_position == expected_x_position2


def test_beam_fitting_validation():
    """Test beam fitting validation and error handling."""
    stock = BeamStock(6000, (60, 120))

    # Test beam that fits
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=60, height=120)
    assert stock.can_fit_element(beam1)

    # Add the beam
    stock.add_element(beam1)

    # Test beam that exactly fits remaining space
    beam2 = Beam(frame=Frame.worldXY(), length=4000, width=60, height=120)
    assert stock.can_fit_element(beam2)

    # Add the beam
    stock.add_element(beam2)

    # Test beam that doesn't fit
    beam3 = Beam(frame=Frame.worldXY(), length=1000, width=60, height=120)
    assert not stock.can_fit_element(beam3)


def test_serialization():
    """Test data serialization and copy functionality."""
    # Create stock with beams
    stock = BeamStock(6000, (60, 120))
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=60, height=120)
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=60, height=120)
    stock.add_element(beam1)
    stock.add_element(beam2)

    # Set spacing
    stock.spacing = 5.0

    # Test serialization
    restored_data = json_loads(json_dumps(stock))
    assert isinstance(restored_data, BeamStock)
    assert restored_data.length == stock.length
    assert restored_data.width == stock.width
    assert restored_data.height == stock.height
    assert restored_data.cross_section == stock.cross_section
    assert restored_data.spacing == stock.spacing

    assert len(restored_data.element_data) == len(stock.element_data)
    assert str(beam1.guid) in restored_data.element_data
    assert str(beam2.guid) in restored_data.element_data
    element_data1 = restored_data.element_data[str(beam1.guid)]
    element_data2 = restored_data.element_data[str(beam2.guid)]
    assert isinstance(element_data1.frame, Frame)
    assert element_data1.key == beam1.name + "-" + str(beam1.guid)[:4]
    assert element_data1.length == beam1.blank_length
    assert isinstance(element_data2.frame, Frame)
    assert element_data2.key == beam2.name + "-" + str(beam2.guid)[:4]
    assert element_data2.length == beam2.blank_length


def test_beam_stock_compatibility():
    """Test BeamStock.is_compatible_with with tolerance."""
    stock = BeamStock(6000, (120.0, 60.0))
    # Test almost identical float dimensions
    beam_float = Beam(frame=Frame.worldXY(), length=2000, width=120.0000001, height=59.9999999)
    assert stock.is_compatible_with(beam_float)

    # Test with a significant difference
    beam_diff = Beam(frame=Frame.worldXY(), length=2000, width=120.1, height=60)
    assert not stock.is_compatible_with(beam_diff)

    # Test with tolerance on square sections
    square_stock = BeamStock(6000, (100, 100))
    beam_square_float = Beam(frame=Frame.worldXY(), length=2000, width=100.0000001, height=99.9999999)
    assert square_stock.is_compatible_with(beam_square_float)


# ============================================================================
# BeamNester Tests
# ============================================================================


def test_beam_nester_initialization():
    """Test BeamNester initialization with valid parameters."""
    model = TimberModel()
    stock_catalog = [
        BeamStock(6000, (120, 60)),
        BeamStock(5000, (80, 40)),
    ]

    nester = BeamNester(model, stock_catalog, spacing=5.0)

    assert nester.model is model
    assert nester.stock_catalog == stock_catalog
    assert nester.spacing == 5.0


def test_beam_nester_single_stock_initialization():
    """Test BeamNester initialization with single stock (not list)."""
    model = TimberModel()
    stock = BeamStock(6000, (120, 60))

    nester = BeamNester(model, stock, 3.0)

    assert nester.model is model
    assert nester.stock_catalog == [stock]  # Should be converted to list
    assert nester.spacing == 3.0


def test_sort_beams_by_stock():
    """Test the sort_beams_by_stock method."""
    model = TimberModel()

    # Add compatible and incompatible beams
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)  # Compatible
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=200, height=100)  # Incompatible
    beam3 = Beam(frame=Frame.worldXY(), length=1000, width=60, height=120)  # Compatible

    model.add_element(beam1)
    model.add_element(beam2)
    model.add_element(beam3)

    stock_catalog = [BeamStock(6000, (120, 60))]
    nester = BeamNester(model, stock_catalog)

    # Test sorting with warning capture
    with pytest.warns(UserWarning, match="Found 1 beam\\(s\\) incompatible.*200x100M"):
        stock_beam_map = nester._sort_beams_by_stock(model.beams)

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
    stock = BeamStock(6000, (120, 60))

    result_stocks = BeamNester._first_fit_decreasing(beams, stock)

    # Should have 2 stocks: first with beam1+beam4 (5500), second with beam2+beam3 (3500)
    assert len(result_stocks) == 2

    # Check first stock - gets beam1 (3000) + beam4 (2500) = 5500
    assert len(result_stocks[0].element_data) == 2
    assert str(beam1.guid) in result_stocks[0].element_data
    assert str(beam4.guid) in result_stocks[0].element_data

    # Check second stock - gets beam2 (2000) + beam3 (1500) = 3500
    assert len(result_stocks[1].element_data) == 2
    assert str(beam2.guid) in result_stocks[1].element_data
    assert str(beam3.guid) in result_stocks[1].element_data


def test_best_fit_decreasing_single_stock():
    """Test Best Fit Decreasing algorithm for single stock type."""
    # Create beams of specific lengths to test best fit behavior
    beam1 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam3 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)  # Should fit with beam1
    beam4 = Beam(frame=Frame.worldXY(), length=500, width=120, height=60)

    beams = [beam1, beam2, beam3, beam4]
    stock = BeamStock(6000, (120, 60))

    result_stocks = BeamNester._best_fit_decreasing(beams, stock)

    # Should have 2 stocks: first with beam1+beam3 (6000), second with beam2+beam4 (2500)
    assert len(result_stocks) == 2

    # Check first stock (beam1 + beam3)
    assert len(result_stocks[0].element_data) == 2
    assert str(beam1.guid) in result_stocks[0].element_data
    assert str(beam3.guid) in result_stocks[0].element_data

    # Check second stock (beam2 + beam4)
    assert len(result_stocks[1].element_data) == 2
    assert str(beam2.guid) in result_stocks[1].element_data
    assert str(beam4.guid) in result_stocks[1].element_data


def test_nest_beams_no_compatible_stock():
    """Test nesting when no stock matches beam cross-sections."""
    model = TimberModel()

    # Add beam with cross-section not in catalog
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=200, height=100)
    model.add_element(beam1)

    stock_catalog = [BeamStock(6000, (120, 60))]

    nester = BeamNester(model, stock_catalog)

    # Should warn about incompatible beam cross-section
    with pytest.warns(UserWarning, match="Found 1 beam\\(s\\) incompatible.*200x100M"):
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

    stock_catalog = [BeamStock(6000, (120, 60))]

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
        assert "200x100M" in warning_message
        assert "150x80M" in warning_message


def test_nest_beams_empty_model():
    """Test nesting with empty model (no beams)."""
    model = TimberModel()
    stock_catalog = [BeamStock(6000, (120, 60))]

    nester = BeamNester(model, stock_catalog)
    nesting_result = nester.nest()

    # Should return empty list since no beams to nest
    assert len(nesting_result.stocks) == 0


def test_nest_method_basic_functionality_fast():
    """Test BeamNester.nest() method with basic nesting scenario."""
    model = TimberModel()

    # Add beams with compatible cross-sections
    beam1 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam3 = Beam(frame=Frame.worldXY(), length=500, width=120, height=60)

    model.add_element(beam1)
    model.add_element(beam2)
    model.add_element(beam3)

    stock_catalog = BeamStock(6000, (120, 60))
    nester = BeamNester(model, stock_catalog, spacing=5.0)

    # Test nest() method
    nesting_result = nester.nest(fast=True)

    # Should return NestingResult instance
    assert isinstance(nesting_result, NestingResult)
    assert len(nesting_result.stocks) == 1  # All beams should fit in one stock

    # Check that all beams are assigned
    all_element_guids = set()
    for stock in nesting_result.stocks:
        assert stock.spacing == nester.spacing
        all_element_guids.update(stock.element_data.keys())

    expected_guids = {str(beam1.guid), str(beam2.guid), str(beam3.guid)}
    assert all_element_guids == expected_guids


def test_nest_method_basic_functionality_slow():
    """Test BeamNester.nest() method with basic nesting scenario."""
    model = TimberModel()

    # Add beams with compatible cross-sections
    beam1 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam3 = Beam(frame=Frame.worldXY(), length=500, width=120, height=60)

    model.add_element(beam1)
    model.add_element(beam2)
    model.add_element(beam3)

    stock_catalog = BeamStock(6000, (120, 60))
    nester = BeamNester(model, stock_catalog, spacing=5.0)

    # Test nest() method
    nesting_result = nester.nest(fast=False)

    # Should return NestingResult instance
    assert isinstance(nesting_result, NestingResult)
    assert len(nesting_result.stocks) == 1  # All beams should fit in one stock

    # Check that all beams are assigned
    all_element_guids = set()
    for stock in nesting_result.stocks:
        assert stock.spacing == nester.spacing
        all_element_guids.update(stock.element_data.keys())

    expected_guids = {str(beam1.guid), str(beam2.guid), str(beam3.guid)}
    assert all_element_guids == expected_guids


def test_nest_method_with_incompatible_beams():
    """Test BeamNester.nest() method with incompatible beams."""
    model = TimberModel()

    # Add compatible and incompatible beams
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)  # Compatible
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=200, height=100)  # Incompatible

    model.add_element(beam1)
    model.add_element(beam2)

    stock_catalog = [BeamStock(6000, (120, 60))]
    nester = BeamNester(model, stock_catalog)

    # Should warn about incompatible beam
    with pytest.warns(UserWarning, match="Found 1 beam\\(s\\) incompatible.*200x100M"):
        nesting_result = nester.nest()

    # Should have one stock with only the compatible beam
    assert isinstance(nesting_result, NestingResult)
    assert len(nesting_result.stocks) == 1
    assert str(beam1.guid) in nesting_result.stocks[0].element_data
    assert str(beam2.guid) not in nesting_result.stocks[0].element_data


def test_nest_per_group_basic():
    """Test per_group nesting keeps beams from the same group together on separate stocks."""
    model = TimberModel()
    polyline = Polyline([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0), (0, 1000, 0), (0, 0, 0)])
    # Create Group A with 2 beams
    group_a = Panel.from_outline_thickness(outline=polyline, thickness=0)
    beam_a1 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam_a2 = Beam(frame=Frame.worldXY(), length=1500, width=120, height=60)
    model.add_element(group_a)
    model.add_element(beam_a1, parent=group_a)
    model.add_element(beam_a2, parent=group_a)

    # Create Group B with 2 beams
    group_b = Panel.from_outline_thickness(outline=polyline, thickness=0)
    beam_b1 = Beam(frame=Frame.worldXY(), length=800, width=120, height=60)
    beam_b2 = Beam(frame=Frame.worldXY(), length=1200, width=120, height=60)
    model.add_element(group_b)
    model.add_element(beam_b1, parent=group_b)
    model.add_element(beam_b2, parent=group_b)

    stock_catalog = [BeamStock(3000, (120, 60))]

    # Test without per_group (all beams optimized together)
    nester_global = BeamNester(model, stock_catalog, per_group=False)
    result_global = nester_global.nest()

    # Test with per_group (each group nested separately)
    nester_grouped = BeamNester(model, stock_catalog, per_group=True)
    result_grouped = nester_grouped.nest()

    # Global optimization: all 4 beams optimized together
    # Sorted descending: 2000, 1500, 1200, 800
    # Stock 1: 2000 + 800 = 2800, Stock 2: 1500 + 1200 = 2700
    assert len(result_global.stocks) == 2

    # Per-group: each group nested separately
    # Group A (3500 total) fits in 2 stocks, Group B (2000 total) fits in 1 stocks
    assert len(result_grouped.stocks) == 3

    # Verify all beams are nested in both cases
    all_beams = {str(beam_a1.guid), str(beam_a2.guid), str(beam_b1.guid), str(beam_b2.guid)}

    global_guids = set()
    for stock in result_global.stocks:
        global_guids.update(stock.element_data.keys())
    assert global_guids == all_beams

    grouped_guids = set()
    for stock in result_grouped.stocks:
        grouped_guids.update(stock.element_data.keys())
    assert grouped_guids == all_beams


def test_nest_per_group_with_standalone_beams():
    """Test per_group nesting handles both grouped and standalone beams correctly."""
    model = TimberModel()
    polyline = Polyline([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0), (0, 1000, 0), (0, 0, 0)])

    # Create a group with 2 beams
    group = Panel.from_outline_thickness(outline=polyline, thickness=0)
    beam_g1 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam_g2 = Beam(frame=Frame.worldXY(), length=1500, width=120, height=60)
    model.add_element(group)
    model.add_element(beam_g1, parent=group)
    model.add_element(beam_g2, parent=group)

    # Add standalone beams (not in a group)
    beam_s1 = Beam(frame=Frame.worldXY(), length=1000, width=120, height=60)
    beam_s2 = Beam(frame=Frame.worldXY(), length=800, width=120, height=60)
    model.add_element(beam_s1)
    model.add_element(beam_s2)

    stock_catalog = [BeamStock(6000, (120, 60))]
    nester = BeamNester(model, stock_catalog, per_group=True)
    result = nester.nest()

    # Per-group should create 2 stocks:
    # Stock 1: grouped beams (2000 + 1500 = 3500)
    # Stock 2: standalone beams (1000 + 800 = 1800)
    assert len(result.stocks) == 2

    # All beams should be nested
    all_beams = {str(beam_g1.guid), str(beam_g2.guid), str(beam_s1.guid), str(beam_s2.guid)}

    nested_guids = set()
    for stock in result.stocks:
        nested_guids.update(stock.element_data.keys())

    assert nested_guids == all_beams


def test_nest_per_group_empty_groups():
    """Test per_group nesting handles empty groups without beams."""
    model = TimberModel()
    polyline = Polyline([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0), (0, 1000, 0), (0, 0, 0)])

    # Create an empty group
    empty_group = Panel.from_outline_thickness(outline=polyline, thickness=0)
    model.add_element(empty_group)

    # Add a group with beams
    group_with_beams = Panel.from_outline_thickness(outline=polyline, thickness=0)
    beam1 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=1500, width=120, height=60)
    model.add_element(group_with_beams)
    model.add_element(beam1, parent=group_with_beams)
    model.add_element(beam2, parent=group_with_beams)

    stock_catalog = [BeamStock(6000, (120, 60))]
    nester = BeamNester(model, stock_catalog, per_group=True)
    result = nester.nest()

    # Should only create stocks for the group with beams
    assert len(result.stocks) == 1
    # All beams should be nested
    all_beams = {str(beam1.guid), str(beam2.guid)}
    nested_guids = set()
    for stock in result.stocks:
        nested_guids.update(stock.element_data.keys())
    assert nested_guids == all_beams


def test_nest_per_group_multiple_sections():
    """Test per_group nesting with groups having beams of different cross-sections."""
    model = TimberModel()
    polyline = Polyline([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0), (0, 1000, 0), (0, 0, 0)])
    # Create Group A with beams of multiple cross-sections
    group_a = Panel.from_outline_thickness(outline=polyline, thickness=0)
    beam_a1 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam_a2 = Beam(frame=Frame.worldXY(), length=1500, width=80, height=40)
    model.add_element(group_a)
    model.add_element(beam_a1, parent=group_a)
    model.add_element(beam_a2, parent=group_a)

    # Add standalone beams with same cross-sections
    beam_s1 = Beam(frame=Frame.worldXY(), length=1000, width=120, height=60)
    beam_s2 = Beam(frame=Frame.worldXY(), length=800, width=80, height=40)
    model.add_element(beam_s1)
    model.add_element(beam_s2)

    stock_catalog = [BeamStock(6000, (120, 60)), BeamStock(6000, (80, 40))]
    nester = BeamNester(model, stock_catalog, per_group=True)
    result = nester.nest()

    # Should create 2 stocks for Group A (one per cross-section) and 2 for standalone beams
    assert len(result.stocks) == 4
    # All beams should be nested
    all_beams = {str(beam_a1.guid), str(beam_a2.guid), str(beam_s1.guid), str(beam_s2.guid)}
    nested_guids = set()
    for stock in result.stocks:
        nested_guids.update(stock.element_data.keys())
    assert nested_guids == all_beams


# ============================================================================
# NestingResult Tests
# ============================================================================


def test_nesting_result_basic_properties():
    """Test NestingResult basic properties and functionality."""
    # Create some test stocks with beams
    stock1 = BeamStock(6000, (120, 60))
    stock2 = BeamStock(6000, (120, 60))

    beam1 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)

    stock1.add_element(beam1)
    stock2.add_element(beam2)

    stocks = [stock1, stock2]
    result = NestingResult(stocks)

    # Test basic properties
    assert result.stocks == stocks
    assert len(result.stocks) == 2

    # Test total_material_volume
    expected_volume = 2 * (6000 * 120 * 60)  # 2 stocks of same dimensions
    assert result.total_material_volume == expected_volume

    # Test total_stock_pieces - should return detailed report
    stock_pieces = result.total_stock_pieces
    assert isinstance(stock_pieces, dict)
    assert "BeamStock" in stock_pieces
    assert "Dimensions(M): 120.000x60.000x6000.000" in stock_pieces["BeamStock"]
    assert stock_pieces["BeamStock"]["Dimensions(M): 120.000x60.000x6000.000"] == 2  # 2 pieces of this dimension


def test_nesting_result_serialization():
    """Test NestingResult serialization functionality."""
    # Create test stock with beam
    stock = BeamStock(6000, (120, 60))
    beam = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    stock.add_element(beam)

    result = NestingResult(stock)

    # Test serialization
    data = result.__data__
    assert len(data["stocks"]) == 1

    # Test deserialization
    restored_result = NestingResult.__from_data__(data)
    assert len(restored_result.stocks) == 1
    assert isinstance(restored_result.stocks[0], BeamStock)
    assert restored_result.stocks[0].length == stock.length
    assert restored_result.stocks[0].width == stock.width
    assert restored_result.stocks[0].height == stock.height
    assert restored_result.stocks[0].spacing == stock.spacing

    # Test that properties match between original and restored
    assert restored_result.total_material_volume == result.total_material_volume
    assert restored_result.total_stock_pieces == result.total_stock_pieces


def test_nesting_result_summary_output():
    """Test the output format of the NestingResult summary property."""
    stock = BeamStock(6000, (120, 60), spacing=5.0)
    beam = Beam(frame=Frame.worldXY(), length=2000, width=120, height=60)
    beam.name = "B1"
    stock.add_element(beam)

    result = NestingResult(stock)
    summary = result.summary

    assert "BeamStock_0:" in summary
    assert "Dimensions(M): 120.000x60.000x6000.000" in summary
    assert "BeamKeys: ['B1-{}']".format(str(beam.guid)[:4]) in summary
    assert "BeamLengths(M): [2000.000]" in summary
    assert "Waste(M): 4000.000" in summary
    assert "Spacing(M): 5.000" in summary


def test_nesting_result_properties():
    """Test NestingResult summary properties."""
    stock1 = BeamStock(6000, (120.000, 60.000))
    stock2 = BeamStock(5000, (80.00, 40.00))
    stock3 = BeamStock(6000, (120, 60))  # Duplicate stock type

    beam1 = Beam(frame=Frame.worldXY(), length=3000, width=120, height=60)
    beam2 = Beam(frame=Frame.worldXY(), length=2000, width=80, height=40)
    beam3 = Beam(frame=Frame.worldXY(), length=1500, width=80, height=40)

    stock1.add_element(beam1)
    stock2.add_element(beam2)
    stock2.add_element(beam3)

    result = NestingResult([stock1, stock2, stock3])

    # Test total_material_volume
    expected_volume = (6000 * 120 * 60) + (5000 * 80 * 40) + (6000 * 120 * 60)
    assert result.total_material_volume == expected_volume

    # Test total_stock_pieces
    stock_pieces = result.total_stock_pieces
    assert stock_pieces["BeamStock"]["Dimensions(M): 120.000x60.000x6000.000"] == 2
    assert stock_pieces["BeamStock"]["Dimensions(M): 80.000x40.000x5000.000"] == 1

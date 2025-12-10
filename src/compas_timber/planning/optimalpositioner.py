from compas.tolerance import TOL

from compas_timber.connections import beam_ref_side_incidence_with_vector
from compas_timber.fabrication import Lap
from compas_timber.fabrication import LongitudinalCutProxy
from compas_timber.fabrication.btlx import MachiningLimits

# Gripper's Position Parameters
GRIPPER_SEPARATION = 500.0

# Gripper's Laps Parameters
LAP_LENGTH = 110.0
LAP_DEPTH = 80.0
LAP_WIDTH = 140.0

# Existing Laps Parameters
LAP_THRESHOLD = 10.0
ADJUST_STEP = 5.0

# Consoles Position Parameters
CONSOLE_WIDTH = 140.0

def set_gripper_positions(model):
    for beam in model.beams:
        # determine gripper positions for each beam
        gripper_positions = _get_gripper_positions(beam)
        if not gripper_positions:
            print((f"Could not determine valid gripper positions for beam of length {beam.blank_length} mm."))
            gripper_positions = [beam.blank_length * 0.5]
            beam.attributes["gripper_position"] = gripper_positions[0]
        else:
            if len(gripper_positions) == 2:
                # the gripper positions should respect the desired separation
                assert TOL.is_close(GRIPPER_SEPARATION, gripper_positions[1] - gripper_positions[0])
                # store the central gripper position as beam attribute
                beam.attributes["gripper_position"] = (sum(gripper_positions) + LAP_LENGTH) * 0.5
            elif len(gripper_positions) == 1:
                beam.attributes["gripper_position"] = gripper_positions[0] - (GRIPPER_SEPARATION - LAP_LENGTH) * 0.5
            else:
                raise ValueError("Unexpected number of gripper positions returned.")

        # add gripper laps to the beams that have a longitudinal cut
        if beam.width >= LAP_WIDTH and beam.height >= LAP_WIDTH:
            for f in beam.features:
                if isinstance(f, LongitudinalCutProxy):
                    long_plane = f.plane.transformed(beam.modeltransformation)
                    ref_side_dict = beam_ref_side_incidence_with_vector(beam, long_plane.normal, ignore_ends=True)
                    ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
                    if ref_side_index not in [1, 3]:
                        raise ValueError("Cannot place gripper lap on beam with square cross-section and longitudinal cut not on side 1 or 3.")

            depth = LAP_DEPTH
            if TOL.is_close(beam.width, 280.0) or TOL.is_close(beam.height, 280.0):
                depth += 140.0

            if isinstance(gripper_positions, (list, tuple)):
                for g in list(gripper_positions):
                    lap = Lap(
                        start_x=float(g),
                        start_y=0.0,
                        length=float(LAP_LENGTH),
                        width=float(LAP_WIDTH),
                        depth=depth,
                        machining_limits=MachiningLimits().limits,
                        ref_side_index=ref_side_index,
                        is_joinery=False,
                    )
                    lap.name = "GripperLap"
                    beam.add_feature(lap)
            else:
                lap = Lap(
                    start_x=float(gripper_positions),
                    start_y=0.0,
                    length=float(LAP_LENGTH),
                    width=float(LAP_WIDTH),
                    depth=depth,
                    machining_limits=MachiningLimits().limits,
                    ref_side_index=ref_side_index,
                    is_joinery=False,
                )
                lap.name = "GripperLap"
                beam.add_feature(lap)
        else:
            beam.attributes["gripper_position"] = beam.blank_length * 0.5


def _domains_overlap(domain1, domain2, tolerance=0.1):
    """
    Check if two domains overlap at all.
    Two intervals overlap if: start1 < end2 AND start2 < end1
    Added small tolerance to handle floating point precision issues.
    """
    # Add small tolerance for floating point comparisons
    return (domain1[0] - tolerance) < domain2[1] and (domain2[0] - tolerance) < domain1[1]


def _positions_are_valid(positions, usable_domain, lap_domains):
    """
    Check if gripper positions are valid.

    Each gripper position defines a domain [pos, pos + LAP_LENGTH].
    Positions are valid if:
    1. All gripper domains are within beam bounds
    2. Gripper domains don't overlap with lap domains beyond max_overlap_ratio
    """
    # Create gripper domains
    gripper_domains = [(pos, pos + LAP_LENGTH) for pos in positions]

    # Check beam bounds
    for domain in gripper_domains:
        if domain[0] < usable_domain[0] or domain[1] > usable_domain[1]:
            return False

    # Check overlap with lap domains
    for gripper_domain in gripper_domains:
        if not lap_domains:
            return True
        for lap_domain in lap_domains:
            if _domains_overlap(gripper_domain, lap_domain):
                return False
    return True


def _get_lap_domains(beam):
    """Get lap domains for all laps EXCEPT GripperLaps (to avoid checking against themselves).

    Note: start_x is ALWAYS an absolute position from the start of the beam,
    regardless of orientation. The orientation affects the cutting direction,
    not the coordinate system.
    """
    lap_features = [f for f in beam.features if f.__class__.__name__ == "Lap"]
    lap_domains = []
    for lap in lap_features:
        # start_x is absolute position from beam start for both orientations
        if lap.orientation == "start":
            # For START orientation, lap extends forward from start_x
            lap_domain = (lap.start_x, lap.start_x + lap.length)
            lap_domains.append(lap_domain)
        elif lap.orientation == "end":
            # For END orientation, lap extends backward from start_x
            lap_domain = (lap.start_x - lap.length, lap.start_x)
            lap_domains.append(lap_domain)
    return lap_domains


def _define_gripper_positions(usable_domain):
    center = (usable_domain[0] + usable_domain[1]) * 0.5
    if (usable_domain[1] - usable_domain[0]) <= GRIPPER_SEPARATION + 2 * LAP_LENGTH:
        return [center]
    else:
        # start by trying to place the grippers at 1/4 and 3/4 of the beam
        return [center - GRIPPER_SEPARATION / 2, center + GRIPPER_SEPARATION / 2]


def _get_usable_domain(beam):
    """Calculate usable domain considering JackRafterCuts.

    Note: start_x is ALWAYS an absolute position from the start of the beam,
    regardless of orientation. The orientation affects the cutting direction,
    not the coordinate system.
    """
    jack_cut_features = [f for f in beam.features if f.__class__.__name__ == "JackRafterCut"]
    start_bound = 0.0
    end_bound = beam.blank_length

    for cut in jack_cut_features:
        # start_x is absolute position from beam start for both orientations
        if cut.orientation == "start":
            # Cut at start - start_x is where the cut is located
            start_bound = max(start_bound, cut.start_x)
        elif cut.orientation == "end":
            # Cut at end - start_x is where the cut is located
            end_bound = min(end_bound, cut.start_x)

    return start_bound, end_bound


def _get_gripper_positions(beam):
    """Return two gripper positions (g1, g2) along a beam of given length.

    Positions are center +/- sep/2 and are clamped to the interior of the
    beam using a small margin to avoid 0 or exact end coordinates. If the
    beam is shorter than the desired separation, the function falls back to
    25%/75% split of the beam.
    """
    usable_domain = _get_usable_domain(beam)

    # collect lap domains for the laps on the beam
    lap_domains = _get_lap_domains(beam)

    # define initial gripper positions according to usable length
    gripper_positions = _define_gripper_positions(usable_domain)

    # check if there are any conflicts, otherwise we are done!
    if _positions_are_valid(gripper_positions, usable_domain, lap_domains):
        return tuple(float(round(g, 3)) for g in gripper_positions)

    # CONFLICT RESOLUTION: Find the first overlap and calculate offsets to clear it
    overlapping_gripper_idx = None
    overlapping_domain_idx = None

    for i, domain in enumerate(lap_domains):
        for j, g_pos in enumerate(gripper_positions):
            gripper_domain = (g_pos, g_pos + LAP_LENGTH)
            if _domains_overlap(gripper_domain, domain):
                overlapping_gripper_idx = j
                overlapping_domain_idx = i
                break
        if overlapping_gripper_idx is not None:
            break

    # If no overlap found, return current positions
    if overlapping_gripper_idx is None:
        return tuple(float(round(g, 3)) for g in gripper_positions)

    # Get the overlapping gripper's position and lap's domain
    g_pos = gripper_positions[overlapping_gripper_idx]
    lap_domain = lap_domains[overlapping_domain_idx]
    gripper_domain = (g_pos, g_pos + LAP_LENGTH)

    # Calculate how much to move to clear the lap domain (with threshold)
    # To move backward (negative): need to move gripper END before lap START
    distance_to_move_backward = gripper_domain[1] - lap_domain[0] + LAP_THRESHOLD
    # To move forward (positive): need to move gripper START after lap END
    distance_to_move_forward = lap_domain[1] - gripper_domain[0] + LAP_THRESHOLD

    # Create offsets (negative for backward, positive for forward)
    offsets = [-distance_to_move_backward, distance_to_move_forward]

    # Prefer the shorter distance
    if distance_to_move_backward > distance_to_move_forward:
        offsets.reverse()

    # Try both offsets (deterministic - one should work)
    for offset in offsets:
        new_positions = [gripper_positions[0] + offset]
        if len(gripper_positions) > 1:
            new_positions.append(gripper_positions[1] + offset)

        if _positions_are_valid(new_positions, usable_domain, lap_domains):
            return tuple(float(round(g, 3)) for g in new_positions)

    # FALLBACK: Try incremental adjustments if both simple offsets failed
    # (e.g., when moving in one direction hits another lap or boundary)
    preferred_offset = offsets[0]
    increment = ADJUST_STEP if preferred_offset > 0 else -ADJUST_STEP

    max_attempts = 100
    for attempt in range(max_attempts):
        test_offset = preferred_offset + (increment * (attempt + 1))
        new_positions = [gripper_positions[0] + test_offset]
        if len(gripper_positions) > 1:
            new_positions.append(gripper_positions[1] + test_offset)

        if _positions_are_valid(new_positions, usable_domain, lap_domains):
            return tuple(float(round(g, 3)) for g in new_positions)

    # No valid position found - return original positions
    return tuple(float(round(g, 3)) for g in gripper_positions)

def _define_consoles_positions(usable_domain, beams_on_stock, beam_index, stock_beam_lengths):
    """Define initial console target positions inside the usable domain.

    Positions are computed relative to the usable domain (i.e. cuts at
    beam ends are respected). The number and locations depend on
    ``beams_on_stock``.

    Returns a list of absolute positions (in the same coordinate as
    beam.start_x) inside the usable domain.
    """
    start, end = float(usable_domain[0]), float(usable_domain[1])
    span = max(0.0, end - start)
    # distribute a fixed total of 6 console positions across the beams
    # and return the positions for this specific beam (by index).

    # Short-beam rule: if usable span is smaller than threshold, return
    # a single console in the middle of the usable domain.

    # Determine number of beams in stock
    try:
        bis = int(beams_on_stock) if beams_on_stock is not None else 0
    except Exception:
        bis = 0

    total_consoles = 6

    # Distribution by length
    counts = [0] * bis

    # ensure positive lengths
    lengths = [max(0.0, float(x)) for x in stock_beam_lengths[:bis]]
    total_length = sum(lengths)
    # if all lengths zero/falsy, fallback to equal distribution
    if total_length <= 0.0:
        base = total_consoles // bis
        remainder = total_consoles % bis
        for i in range(bis):
            counts[i] = base + (1 if i < remainder else 0)
    else:
        # allocate at least 1 to each beam if possible
        min_per_beam = 1 if total_consoles >= bis else 0
        # raw allocation based on length proportion
        raw = [x / total_length * total_consoles for x in lengths]
        # initial floor allocation
        floored = [int(max(min_per_beam, int(r))) for r in raw]
        allocated = sum(floored)
        # compute remainders for distributing remaining consoles
        remainders = [(i, raw[i] - floored[i]) for i in range(bis)]
        # if allocated exceeds total_consoles (rare), reduce from smallest remainders
        if allocated > total_consoles:
            surplus = allocated - total_consoles
            # sort by smallest remainder first to remove
            for i, _ in sorted(remainders, key=lambda x: x[1])[:surplus]:
                if floored[i] > min_per_beam:
                    floored[i] -= 1
            counts = floored
        else:
            # distribute remaining consoles by largest fractional remainder
            remaining = total_consoles - allocated
            for i, _ in sorted(remainders, key=lambda x: x[1], reverse=True)[:remaining]:
                floored[i] += 1
            counts = floored

    # clamp beam_index
    idx = int(beam_index) if beam_index is not None else 0
    if idx < 0:
        idx = 0
    if idx >= bis:
        idx = bis - 1

    consoles_for_beam = counts[idx]

    # map number of consoles to fractional positions within usable span
    if consoles_for_beam >= 3:
        fractions = (1.0 / 6.0, 0.5, 5.0 / 6.0)
    elif consoles_for_beam == 2:
        fractions = (1.0 / 3.0, 2.0 / 3.0)
    elif consoles_for_beam == 1:
        fractions = (0.5,)
    else:
        fractions = ()

    return [start + span * f for f in fractions]

def get_consoles_positions(beam, beams_on_stock, beam_index, stock_beam_lengths):
    """Return console positions for a beam.
    """
    usable_domain = _get_usable_domain(beam)

    # collect lap domains for the laps on the beam
    lap_domains = _get_lap_domains(beam)

    # define initial consoles positions according to usable length
    console_positions = _define_consoles_positions(usable_domain, beams_on_stock, beam_index, stock_beam_lengths)

    # console-specific validity: treat each position as the center of a
    # console of width `CONSOLE_WIDTH` (so domain is [pos-half, pos+half]).
    half_console = float(CONSOLE_WIDTH) * 0.5

    def _console_positions_valid(positions_list):
        for p in positions_list:
            left, right = float(p) - half_console, float(p) + half_console
            if left < usable_domain[0] or right > usable_domain[1]:
                return False
            for lap in lap_domains or []:
                if _domains_overlap((left, right), lap):
                    return False
        return True

    # check if there are any conflicts, otherwise we are done!
    if _console_positions_valid(console_positions):
        return tuple(float(round(g, 3) - half_console) for g in console_positions)

    # CONFLICT RESOLUTION: Find the first overlap and calculate offsets to clear it
    overlapping_console_idx = None
    overlapping_domain_idx = None

    for i, domain in enumerate(lap_domains):
        for j, c_pos in enumerate(console_positions):
            console_domain = (float(c_pos) - half_console, float(c_pos) + half_console)
            if _domains_overlap(console_domain, domain):
                overlapping_console_idx = j
                overlapping_domain_idx = i
                break
        if overlapping_console_idx is not None:
            break

    # If no overlap found, return current positions
    if overlapping_console_idx is None:
        return tuple(float(round(g, 3)) for g in console_positions)

    # Get the overlapping consoles's position and lap's domain
    c_pos = float(console_positions[overlapping_console_idx])
    lap_domain = lap_domains[overlapping_domain_idx]
    console_domain = (c_pos - half_console, c_pos + half_console)

    # Calculate how much to move to clear the lap domain (with threshold)
    # To move backward (negative): need to move console END before lap START
    distance_to_move_backward = console_domain[1] - lap_domain[0] + LAP_THRESHOLD
    # To move forward (positive): need to move console START after lap END
    distance_to_move_forward = lap_domain[1] - console_domain[0] + LAP_THRESHOLD

    # Create offsets (negative for backward, positive for forward)
    offsets = [-distance_to_move_backward, distance_to_move_forward]

    # Prefer the shorter distance
    if distance_to_move_backward > distance_to_move_forward:
        offsets.reverse()

    # Try both offsets (deterministic - one should work)
    for offset in offsets:
        new_positions = [float(console_positions[0]) + offset]
        if len(console_positions) > 1:
            new_positions.append(float(console_positions[1]) + offset)

        if _console_positions_valid(new_positions):
            return tuple(float(round(g, 3)) for g in new_positions)

    # FALLBACK: Try incremental adjustments if both simple offsets failed
    # (e.g., when moving in one direction hits another lap or boundary)
    preferred_offset = offsets[0]
    increment = ADJUST_STEP if preferred_offset > 0 else -ADJUST_STEP

    max_attempts = 100
    for attempt in range(max_attempts):
        test_offset = preferred_offset + (increment * (attempt + 1))
        new_positions = [float(console_positions[0]) + test_offset]
        if len(console_positions) > 1:
            new_positions.append(float(console_positions[1]) + test_offset)

        if _console_positions_valid(new_positions):
            return tuple(float(round(g, 3)) for g in new_positions)

    # No valid position found - return original positions
    return tuple(float(round(g, 3)) for g in console_positions)

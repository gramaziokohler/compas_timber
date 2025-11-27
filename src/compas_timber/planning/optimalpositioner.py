from typing import Optional
from typing import Tuple

from compas.geometry import Frame
from compas.geometry import Plane
from compas.tolerance import TOL

from compas_timber.connections import beam_ref_side_incidence_with_vector
from compas_timber.fabrication import Lap
from compas_timber.fabrication import LongitudinalCut
from compas_timber.fabrication.btlx import MachiningLimits

# Grippers Parameters
GRIPPER_SEPARATION = 500.0
SMALL_BEAM_THRESHOLD = 900.0
MIN_MARGIN = 1.0

# Laps Parameters
LAP_LENGTH = 110.0
LAP_DEPTH = 80.0
LAP_WIDTH = 140.0
REF_SIDE_INDEX = 1

# Consoles Parameters
LAP_THRESHOLD = 10.0
ADJUST_STEP = 5.0


def set_gripper_positions(model):
    for beam in model.beams:
        if beam.width >= LAP_WIDTH and beam.height >= LAP_WIDTH:
            for f in beam.features:
                if isinstance(f, LongitudinalCut):
                    long_plane = f.plane_from_params_and_beam(beam)
                    ref_side_dict = beam_ref_side_incidence_with_vector(beam, long_plane.normal, ignore_ends=True)
                    ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
                    if ref_side_index not in [1, 3]:
                        raise ValueError("Cannot place gripper lap on beam with square cross-section and longitudinal cut not on side 1 or 3.")

            gripper_positions = _get_gripper_positions(beam)
            if not gripper_positions:
                continue

            assert TOL.is_close(GRIPPER_SEPARATION, gripper_positions[1] - gripper_positions[0]) if len(gripper_positions) == 2 else True
            beam.attribuites["gripper_position"] = gripper_positions[0]

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
    jack_cut_featurs = [f for f in beam.features if f.__class__.__name__ == "JackRafterCut"]
    start_bound = 0.0
    end_bound = beam.blank_length

    for cut in jack_cut_featurs:
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

    # define initial fripper positions according to usable length
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

    # No valid position found - return None to signal failure
    return None


def get_consoles_positions(
    beam: object,
    g1: Optional[float] = None,
    g2: Optional[float] = None,
    threshold: float = 100.0,
    step: float = 5.0,
    beams_on_stock: Optional[int] = None,
) -> Tuple[float, ...]:
    """Return console positions for a beam.

    By default the function returns two console positions near 1/4 and 3/4
    of the beam length. When the caller knows how many beams are nested on
    the same stock, it can pass ``beams_on_stock`` to alter the number of
    consoles per beam:

    - ``beams_on_stock == 3`` -> return 2 consoles (at ~1/3 and ~2/3)
    - ``beams_on_stock == 2`` -> return 3 consoles (at ~1/6, 1/2, 5/6)

    The function will attempt to shift each console away from the two
    grippers (``g1``, ``g2``) and keep them at least ``threshold`` mm away
    from any lap start in ``lap_starts``. Movement proceeds in ``step``
    increments until a valid position is found or the beam bounds are
    reached.
    """

    length = float(beam.blank_length)
    lap_starts = [f.start_x for f in beam.features if f.__class__.__name__ == "Lap"]

    # (short-beam single-console handling is applied after adjust_one is defined)

    # New rule: if beams_on_stock is 2 or less -> return 3 consoles
    #           if beams_on_stock is 3 or more -> return 2 consoles
    if beams_on_stock is not None:
        try:
            bis = int(beams_on_stock)
        except Exception:
            bis = None
    else:
        bis = None

    if bis is not None and bis <= 2:
        targets = [float(length) * (1.0 / 6.0), float(length) * 0.5, float(length) * (5.0 / 6.0)]
    elif bis is not None and bis >= 3:
        targets = [float(length) * (1.0 / 3.0), float(length) * (2.0 / 3.0)]
    else:
        # default fallback: two consoles at 1/4 and 3/4
        targets = [float(length) * 0.25, float(length) * 0.75]
    minv, maxv = float(MIN_MARGIN), float(max(MIN_MARGIN, length - MIN_MARGIN))

    try:
        if g1 is not None:
            g1 = float(g1)
    except Exception:
        g1 = None
    try:
        if g2 is not None:
            g2 = float(g2)
    except Exception:
        g2 = None
    try:
        lap_list = [float(s) for s in (lap_starts or []) if s is not None]
    except Exception:
        lap_list = []

    def is_valid(x: float) -> bool:
        if x < minv or x > maxv:
            return False
        if g1 is not None and abs(x - g1) < threshold:
            return False
        if g2 is not None and abs(x - g2) < threshold:
            return False
        for s in lap_list:
            if abs(x - s) < threshold:
                return False
        return True

    def adjust_one(initial: float) -> float:
        x = float(max(minv, min(maxv, initial)))
        if is_valid(x):
            return x
        dir = 1
        nearest = None
        if g1 is not None or g2 is not None:
            # pick nearest gripper
            candidates = [p for p in (g1, g2) if p is not None]
            if candidates:
                nearest = min(candidates, key=lambda p: abs(initial - p))
                dir = -1 if initial < nearest else 1

        max_iter = int((maxv - minv) / max(step, 1e-6)) + 1
        for _ in range(max_iter):
            nx = x + dir * step
            if nx < minv or nx > maxv:
                break
            if is_valid(nx):
                return float(max(minv, min(maxv, nx)))
            x = nx

        dir = -dir
        x = float(max(minv, min(maxv, initial)))
        for _ in range(max_iter):
            nx = x + dir * step
            if nx < minv or nx > maxv:
                break
            if is_valid(nx):
                return float(max(minv, min(maxv, nx)))
            x = nx

        return float(max(minv, min(maxv, initial)))

    # Short-beam special case: return a single console at the (adjusted)
    # midpoint when the beam is shorter than SMALL_BEAM_THRESHOLD.
    try:
        if SMALL_BEAM_THRESHOLD is not None and float(length) < float(SMALL_BEAM_THRESHOLD):
            mid = float(round(length / 2.0, 3))
            adj_mid = float(round(adjust_one(mid), 3))
            return (adj_mid,)
    except Exception:
        # fall back to normal logic on error
        pass

    adjusted = []
    for t in targets:
        adjusted.append(float(round(adjust_one(t), 3)))

    return tuple(adjusted)


# LAPS


def _make_world_frame(beam, gx: float):
    try:
        base = beam.ref_frame
        if base is None:
            return None
        origin = base.point.translated(base.xaxis * float(gx))
        return Frame(origin, base.xaxis, base.yaxis)
    except Exception:
        return None


def create_gripper_laps_for_beam(model, beam_index: int, g1: float, g2: float):
    """Create two gripper laps on the beam at start_x g1 and g2.

    This function mutates the given ``model`` by attaching Lap features to the
    specified beam. It tries a plane-based factory first and falls back to the
    Lap constructor with permissive machining limits.

    Returns the mutated model.
    """
    if Lap is None:
        raise RuntimeError("compas_timber not available: cannot create Lap features")

    beams = model.beams
    if beam_index < 0 or beam_index >= len(beams):
        raise IndexError("beam_index out of range")

    beam = beams[beam_index]
    for gx in (g1, g2):
        try:
            try:
                blen = float(beam.length or beam.xsize or beam.blank_length or 0.0)
            except Exception:
                blen = 0.0

            # clamp requested start_x to the beam length to avoid extending beams
            gx_clamped = gx
            if blen and blen > 0:
                try:
                    gx_clamped = max(0.0, min(blen, float(gx)))
                except Exception:
                    gx_clamped = gx
            else:
                try:
                    gx_clamped = float(gx)
                except Exception:
                    gx_clamped = gx

            # skip beams explicitly marked as 'recess' or 'stud' (accept
            # either 'stud' or 'studs' spelling, and tolerate misspelling
            # 'caterogy')
            attrs = {}
            try:
                attrs = getattr(beam, "attributes", {}) or {}
            except Exception:
                attrs = {}
            try:
                cat = attrs.get("category") or attrs.get("caterogy") or ""
            except Exception:
                cat = ""
            try:
                if isinstance(cat, str) and cat.lower() in ("stud", "studs", "recess"):
                    continue
            except Exception:
                pass

            world_frame = _make_world_frame(beam, gx_clamped)
            if world_frame is None:
                continue

            # keep any existing longitudinal cuts if present (optional)
            cuts = [f for f in beam.features or [] if f.__class__.__name__ == "LongitudinalCut"]

            # choose ref side (prefer data from a longitudinal cut if available)
            chosen_rs = None
            try:
                chosen_cut = None
                if cuts:
                    for c in cuts:
                        try:
                            sx = float(getattr(c, "start_x", getattr(c, "data", {}).get("start_x", None)))
                            clen = float(getattr(c, "length", getattr(c, "data", {}).get("length", None) or 0.0))
                        except Exception:
                            sx = None
                            clen = None
                        if sx is not None and clen is not None and gx >= sx and gx <= sx + clen:
                            chosen_cut = c
                            break
                    if chosen_cut is None:
                        chosen_cut = cuts[0]
                    try:
                        chosen_rs = int(getattr(chosen_cut, "ref_side_index", None) or getattr(chosen_cut, "data", {}).get("ref_side_index", None))
                    except Exception:
                        chosen_rs = None
            except Exception:
                chosen_rs = None

            ref_side = REF_SIDE_INDEX if REF_SIDE_INDEX is not None else (chosen_rs if chosen_rs is not None else 0)

            # attempt plane-based creation
            lap = None
            try:
                plane = Plane(world_frame.point, world_frame.zaxis)
                lap = Lap.from_plane_and_beam(plane, beam, length=float(LAP_LENGTH), depth=float(LAP_DEPTH), ref_side_index=ref_side)
            except Exception:
                lap = None

            # fallback to permissive constructor
            if lap is None:
                try:
                    ml = MachiningLimits() if MachiningLimits is not None else None
                    if ml is not None:
                        ml.face_limited_top = False
                        ml.face_limited_front = False
                        ml.face_limited_back = False
                        ml.face_limited_bottom = False
                        lap = Lap(length=float(LAP_LENGTH), width=float(LAP_WIDTH), depth=float(LAP_DEPTH), machining_limits=ml.limits)
                    else:
                        lap = Lap(length=float(LAP_LENGTH), width=float(LAP_WIDTH), depth=float(LAP_DEPTH))
                except Exception:
                    lap = None

            if lap is None:
                continue

            # set conservative/default attributes
            try:
                setattr(lap, "ref_side_index", int(ref_side))
            except Exception:
                pass
            try:
                lap.start_x = float(gx_clamped)
            except Exception:
                try:
                    setattr(lap, "start_x", float(gx_clamped))
                except Exception:
                    pass
            try:
                setattr(lap, "start_y", 0.0)
            except Exception:
                pass
            try:
                setattr(lap, "width", float(LAP_WIDTH))
            except Exception:
                pass
            try:
                setattr(lap, "ysize", float(LAP_WIDTH))
            except Exception:
                pass
            try:
                setattr(lap, "depth", float(LAP_DEPTH))
            except Exception:
                pass
            try:
                setattr(lap, "inclination", 90.0)
            except Exception:
                pass
            try:
                setattr(lap, "angle", 90.0)
            except Exception:
                pass
            try:
                setattr(lap, "orientation", "start")
            except Exception:
                pass
            try:
                setattr(lap, "slope", 0.0)
            except Exception:
                pass

            # attach
            try:
                beam.add_feature(lap)
            except Exception:
                try:
                    beam.add_features([lap])
                except Exception:
                    if beam.features and isinstance(beam.features, list):
                        beam.features.append(lap)
        except Exception:
            # do not abort on single-beam failures
            continue

    return model


def create_gripper_laps(model, gripper_map: dict):
    """Create gripper laps for multiple beams.

    ``gripper_map`` should be a mapping beam_index -> (g1, g2) or a list of
    tuples. The function mutates and returns the model.
    """
    if isinstance(gripper_map, dict):
        items = gripper_map.items()
    else:
        items = list(gripper_map)

    for k, v in items:
        try:
            # allow either a pair (g1, g2) or a single numeric value for
            # small beams (treated as a single gripper location)
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                g1, g2 = v[0], v[1]
            else:
                try:
                    g1 = float(v)
                    g2 = g1
                except Exception:
                    continue
            create_gripper_laps_for_beam(model, int(k), float(g1), float(g2))
        except Exception:
            continue

    return model


def add_gripper_laps_to_model(model, grippers):
    """Add gripper laps to every beam (except those explicitly
    excluded by their `category` attribute).

    ``grippers`` may be provided as a single iterable (``(g1, g2)`` or
    ``[g1, g2]``) or a mapping per-beam. The function will unpack the
    two start_x values and add laps at those positions to each beam.

    The function mutates the model in-place and returns it.
    """
    if isinstance(grippers, dict):
        return create_gripper_laps(model, grippers)

    try:
        if isinstance(grippers, (list, tuple)) and len(grippers) >= 2:
            g1, g2 = float(grippers[0]), float(grippers[1])
        else:
            raise TypeError("grippers must be a (g1,g2) pair or a mapping")
    except Exception:
        raise

    beams = model.beams
    for i, beam in enumerate(beams):
        try:
            try:
                create_gripper_laps_for_beam(model, int(i), g1, g2)
            except Exception:
                continue
        except Exception:
            continue
    return model

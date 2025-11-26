from typing import Tuple, Optional
from compas.geometry import Frame
from compas.geometry import Plane
from compas_timber.fabrication import Lap
from compas_timber.fabrication.btlx import MachiningLimits

# Grippers Parameters
GRIPPER_SEPARATION = 500.0
SMALL_BEAM_THRESHOLD = 900.0
MIN_MARGIN = 1.0

# Laps Parameters
LAP_LENGTH = 110.0
LAP_DEPTH = 60.0
LAP_WIDTH = 140.0
REF_SIDE_INDEX = 3

# Consoles Parameters
LAP_THRESHOLD = 100.0
ADJUST_STEP = 5.0


def gripper_positions(
    beam: object,
    sep: float = GRIPPER_SEPARATION,
    threshold: float = LAP_THRESHOLD,
    step: float = ADJUST_STEP,
    middle: bool = False,
    small_beam_threshold: float = SMALL_BEAM_THRESHOLD,
) -> object:
    """Return two gripper positions (g1, g2) along a beam of given length.

    Positions are center +/- sep/2 and are clamped to the interior of the
    beam using a small margin to avoid 0 or exact end coordinates. If the
    beam is shorter than the desired separation, the function falls back to
    25%/75% split of the beam.
    """
    length = float(beam.blank_length)

    lap_starts = [f.start_x for f in beam.features if f.__class__.__name__ == 'Lap']
    # If the beam is very short, prefer a single gripper located at 1/4
    # from the best side (avoid placing it at the console which will be
    # positioned at the beam midpoint). For backward compatibility we
    # return a pair (g,g) unless `middle=True` is requested.
    try:
        if small_beam_threshold is not None and float(length) < float(small_beam_threshold):

            q1 = float(round(length * 0.25, 3))
            q2 = float(round(length * 0.75, 3))

            # collect lap starts safely
            try:
                lap_list = [float(s) for s in (lap_starts or []) if s is not None]
            except Exception:
                lap_list = []

            def safe_pos(x: float) -> bool:
                if x < MIN_MARGIN or x > max(MIN_MARGIN, length - MIN_MARGIN):
                    return False
                for s in lap_list:
                    if abs(x - s) < threshold:
                        return False
                return True

            cand = None
            # prefer the candidate (q1 or q2) that is safe and farthest from laps
            cands = []
            for c in (q1, q2):
                if safe_pos(c):
                    mind = min([abs(c - s) for s in lap_list]) if lap_list else float('inf')
                    cands.append((mind, c))
            if cands:
                # choose candidate with maximum min-distance to any lap
                cand = max(cands, key=lambda x: x[0])[1]
            else:
                # none safe; fallback to nearest position to q1 that is safe by stepping
                step_count = int(max(10, (length - 2 * MIN_MARGIN) / max(step, 1e-6)))
                found = None
                for i in range(step_count + 1):
                    # try moving inward from q1 and q2 alternately
                    for base in (q1, q2):
                        for d in (i, -i):
                            x = base + d * step
                            if x < MIN_MARGIN or x > max(MIN_MARGIN, length - MIN_MARGIN):
                                continue
                            if safe_pos(x):
                                found = x
                                break
                        if found is not None:
                            break
                    if found is not None:
                        break
                cand = found if found is not None else q1

            g = float(round(cand if cand is not None else q1, 3))
            if middle:
                return g
            # For small beams return a single primitive gripper value
            # (consumers can treat it as a single gripper point).
            return float(round(g, 3))
    except Exception:
        # fall through to normal behavior on error
        pass
    half = float(sep) / 2.0
    center = float(length) / 2.0
    g1 = center - half
    g2 = center + half

    minv, maxv = float(MIN_MARGIN), float(max(MIN_MARGIN, length - MIN_MARGIN))
    if g1 < minv or g2 > maxv:
        if length >= sep + 2.0:
            g1 = max(minv, min(maxv, g1))
            g2 = max(minv, min(maxv, g2))
        else:
            g1 = max(minv, min(maxv, length * 0.25))
            g2 = max(minv, min(maxv, length * 0.75))

    g1 = float(max(minv, min(maxv, g1)))
    g2 = float(max(minv, min(maxv, g2)))

    try:
        lap_list = [float(s) for s in (lap_starts or []) if s is not None]
    except Exception:
        lap_list = []

    def safe(a: float, b: float) -> bool:
        return all(abs(s - a) >= threshold and abs(s - b) >= threshold for s in lap_list)

    if lap_list and not safe(g1, g2):
        orig_g1, orig_g2 = g1, g2
        max_iter = int(max(10, (maxv - minv) / max(step, 1e-6) * 2))
        for _ in range(max_iter):
            if g2 + step > maxv:
                break
            g1 += step
            g2 += step
            if safe(g1, g2):
                g1 = float(max(minv, min(maxv, g1)))
                g2 = float(max(minv, min(maxv, g2)))
                if middle:
                    return float(round((g1 + g2) / 2.0, 3))
                return g1, g2

        g1, g2 = orig_g1, orig_g2
        for _ in range(max_iter):
            if g1 - step < minv:
                break
            g1 -= step
            g2 -= step
            if safe(g1, g2):
                g1 = float(max(minv, min(maxv, g1)))
                g2 = float(max(minv, min(maxv, g2)))
                if middle:
                    return float(round((g1 + g2) / 2.0, 3))
                return g1, g2

    if middle:
        return float(round((g1 + g2) / 2.0, 3))
    return float(round(g1, 3)), float(round(g2, 3))


def consoles_positions(
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
    lap_starts = [f.start_x for f in beam.features if f.__class__.__name__ == 'Lap']

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
                attrs = getattr(beam, 'attributes', {}) or {}
            except Exception:
                attrs = {}
            try:
                cat = (attrs.get('category') or attrs.get('caterogy') or '')
            except Exception:
                cat = ''
            try:
                if isinstance(cat, str) and cat.lower() in ('stud', 'studs', 'recess'):
                    continue
            except Exception:
                pass

            world_frame = _make_world_frame(beam, gx_clamped)
            if world_frame is None:
                continue

            # keep any existing longitudinal cuts if present (optional)
            cuts = [f for f in beam.features or [] if f.__class__.__name__ == 'LongitudinalCut']

            # choose ref side (prefer data from a longitudinal cut if available)
            chosen_rs = None
            try:
                chosen_cut = None
                if cuts:
                    for c in cuts:
                        try:
                            sx = float(getattr(c, 'start_x', getattr(c, 'data', {}).get('start_x', None)))
                            clen = float(getattr(c, 'length', getattr(c, 'data', {}).get('length', None) or 0.0))
                        except Exception:
                            sx = None
                            clen = None
                        if sx is not None and clen is not None and gx >= sx and gx <= sx + clen:
                            chosen_cut = c
                            break
                    if chosen_cut is None:
                        chosen_cut = cuts[0]
                    try:
                        chosen_rs = int(getattr(chosen_cut, 'ref_side_index', None) or getattr(chosen_cut, 'data', {}).get('ref_side_index', None))
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
                setattr(lap, 'ref_side_index', int(ref_side))
            except Exception:
                pass
            try:
                lap.start_x = float(gx_clamped)
            except Exception:
                try:
                    setattr(lap, 'start_x', float(gx_clamped))
                except Exception:
                    pass
            try:
                setattr(lap, 'start_y', 0.0)
            except Exception:
                pass
            try:
                setattr(lap, 'width', float(LAP_WIDTH))
            except Exception:
                pass
            try:
                setattr(lap, 'ysize', float(LAP_WIDTH))
            except Exception:
                pass
            try:
                setattr(lap, 'depth', float(LAP_DEPTH))
            except Exception:
                pass
            try:
                setattr(lap, 'inclination', 90.0)
            except Exception:
                pass
            try:
                setattr(lap, 'angle', 90.0)
            except Exception:
                pass
            try:
                setattr(lap, 'orientation', 'start')
            except Exception:
                pass
            try:
                setattr(lap, 'slope', 0.0)
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


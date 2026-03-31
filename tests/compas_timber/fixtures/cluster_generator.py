import math
import random
from itertools import combinations
from compas.geometry import Line, Point
from compas_timber.elements import Beam


# Minimum angular separation between any two beams in a cluster.
# Prevents near-parallel lines, which cause joint locations to drift arbitrarily far.
_MIN_ANGLE_DEG = 30.0
_MIN_ANGLE_SIN = math.sin(math.radians(_MIN_ANGLE_DEG))
_MIN_ANGLE_COS = math.cos(math.radians(_MIN_ANGLE_DEG))


def _sample_direction(rng):
    """Sample one direction uniformly on the unit sphere."""
    theta = math.acos(rng.uniform(-1.0, 1.0))  # uniform solid angle, not uniform theta
    phi = rng.uniform(0.0, 2.0 * math.pi)
    return (math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta))


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sample_well_spread_directions(rng, n):
    """Sample n line directions with at least _MIN_ANGLE_DEG between any pair.

    Lines are undirected, so d and -d are the same — we compare |d1·d2|.
    Raises RuntimeError if a valid set cannot be found after many attempts.
    """
    accepted = []
    total_attempts = 0
    max_attempts = 100_000

    while len(accepted) < n:
        if total_attempts >= max_attempts:
            raise RuntimeError(f"Could not find {n} directions with minimum angle {_MIN_ANGLE_DEG}°. Try reducing the cluster size or lowering _MIN_ANGLE_DEG.")
        total_attempts += 1
        candidate = _sample_direction(rng)
        # Reject if within _MIN_ANGLE_DEG of any already-accepted direction (or its antipode)
        if all(abs(_dot(candidate, existing)) < _MIN_ANGLE_COS for existing in accepted):
            accepted.append(candidate)

    return accepted


def _sample_in_ball(rng, radius):
    """Sample a point uniformly inside a sphere of given radius (rejection sampling)."""
    while True:
        dx, dy, dz = (rng.uniform(-radius, radius) for _ in range(3))
        if dx * dx + dy * dy + dz * dz <= radius * radius:
            return dx, dy, dz


def beams_clusters(cluster_count, seed=42, jitter=0.0):
    """Generate beam centerlines arranged in clusters of known sizes.

    Each cluster is a group of lines whose centerlines all pass through (or very
    near) the same point. All pairwise joints within a cluster are guaranteed to
    be within `jitter` distance of each other.

    Parameters
    ----------
    cluster_count : int
        Number of clusters to generate per size category.
    seed : int
        Random seed for reproducibility. Default 42.
    jitter : float
        Maximum distance between any two joints within the same cluster.
        Use 0.0 for perfectly exact intersections.

    Returns
    -------
    list[Beam]
    """
    rng = random.Random(seed)

    cluster_specs = [
        (cluster_count, 10),
        (cluster_count, 8),
        (cluster_count, 6),
        (cluster_count, 4),
        (cluster_count, 3),
        (cluster_count, 2),
    ]

    LINE_HALF_LENGTH = 50.0
    CLUSTER_SPACING = 200.0  # >> LINE_HALF_LENGTH so clusters never overlap
    GRID_WIDTH = 10

    # Derivation of JOINT_BALL_RADIUS:
    #   For two beams whose pass-through points are within radius r of cluster center,
    #   and whose directions are at least _MIN_ANGLE_DEG apart, the actual joint
    #   (closest approach midpoint) drifts from center by at most r / sin(θ_min).
    #   Setting r = jitter * sin(θ_min) / 2 bounds the drift to jitter / 2,
    #   so any two joints in the cluster are at most jitter apart. ✓
    JOINT_BALL_RADIUS = jitter * _MIN_ANGLE_SIN / 2.0

    lines = []
    flat_specs = [n_lines for n_clusters, n_lines in cluster_specs for _ in range(n_clusters)]

    for cluster_idx, n_lines in enumerate(flat_specs):
        # Place cluster centers on a regular grid — spacing ensures no cross-cluster joints
        row = cluster_idx // GRID_WIDTH
        col = cluster_idx % GRID_WIDTH
        cx, cy, cz = col * CLUSTER_SPACING, row * CLUSTER_SPACING, 0.0

        # Sample n_lines directions, each at least _MIN_ANGLE_DEG from all others.
        # This is the key guard against the near-parallel drift problem.
        directions = _sample_well_spread_directions(rng, n_lines)

        if jitter == 0.0:
            # Exact case: every beam passes through the cluster center exactly.
            # Every pairwise joint will be exactly at the center. Distance = 0.
            for dx, dy, dz in directions:
                lines.append(
                    Line(
                        Point(cx - dx * LINE_HALF_LENGTH, cy - dy * LINE_HALF_LENGTH, cz - dz * LINE_HALF_LENGTH),
                        Point(cx + dx * LINE_HALF_LENGTH, cy + dy * LINE_HALF_LENGTH, cz + dz * LINE_HALF_LENGTH),
                    )
                )
        else:
            # Jittered case.
            #
            # Naive approach (broken): jitter each beam's pass-through point independently.
            #   → joint drift = O(jitter / sin θ), unbounded for near-parallel lines.
            #
            # This approach (correct): sample the INTENDED joint location for each pair first,
            # then fit each beam through the mean of its intended joint locations.
            #   → all intended joints within JOINT_BALL_RADIUS of center
            #   → all actual joints within jitter/2 of center → within jitter of each other ✓

            # Step 1: for each pair of beams, draw an intended joint location
            # from a ball of radius JOINT_BALL_RADIUS around the cluster center
            intended_joints = {}
            for i, j in combinations(range(n_lines), 2):
                ox, oy, oz = _sample_in_ball(rng, JOINT_BALL_RADIUS)
                intended_joints[(i, j)] = (cx + ox, cy + oy, cz + oz)

            # Step 2: for each beam, compute its pass-through point as the mean of
            # all intended joint locations it participates in.
            # The mean of points all within JOINT_BALL_RADIUS of center is also
            # within JOINT_BALL_RADIUS of center — so pass-through points stay tight.
            for beam_idx, (dx, dy, dz) in enumerate(directions):
                my_joints = [intended_joints[(min(beam_idx, j), max(beam_idx, j))] for j in range(n_lines) if j != beam_idx]
                mean_x = sum(p[0] for p in my_joints) / len(my_joints)
                mean_y = sum(p[1] for p in my_joints) / len(my_joints)
                mean_z = sum(p[2] for p in my_joints) / len(my_joints)

                lines.append(
                    Line(
                        Point(mean_x - dx * LINE_HALF_LENGTH, mean_y - dy * LINE_HALF_LENGTH, mean_z - dz * LINE_HALF_LENGTH),
                        Point(mean_x + dx * LINE_HALF_LENGTH, mean_y + dy * LINE_HALF_LENGTH, mean_z + dz * LINE_HALF_LENGTH),
                    )
                )

    return [Beam.from_centerline(ln, 5, 5) for ln in lines]

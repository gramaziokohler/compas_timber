"""This is a benchmarking script which was used to figure out performance bottlenecks in the analyzers."""

from time import time
import random
import math
from collections import OrderedDict

from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import MaxNCompositeAnalyzer
from compas_timber.connections.analyzers import find_all_clusters
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


def beams(seed=42, jitter=0.0):
    """Generate beam centerlines arranged in clusters of known sizes.

    Each cluster is a group of lines whose centerlines all pass through
    (or very near) the same point. When pairwise joints are computed from
    these beams, all joints within a cluster will share approximately the
    same location — exactly what the clustering algorithm needs to find.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility. Default 42.
    jitter : float
        Optional small random offset applied to each line's individual
        pass-through point to simulate near-intersections rather than
        perfect ones. Use 0.0 for exact intersections.

    Returns
    -------
    lines : list[compas.geometry.Line]
        All generated beam centerlines. 396 lines across 72 clusters.
    cluster_info : list[tuple[Point, int]]
        One entry per cluster: (center_point, n_lines).
        Useful for asserting the correctness of the result.

        6 clusters found with 10 elements
        6 clusters found with 8 elements
        6 clusters found with 6 elements
        6 clusters found with 4 elements
        6 clusters found with 3 elements
        6 clusters found with 2 elements

    """
    rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Cluster definitions: (number_of_clusters, lines_per_cluster)
    # Totals: 12×10 + 12×8 + 12×6 + 12×4 + 12×3 + 12×2 = 396 lines
    # ------------------------------------------------------------------
    cluster_specs = [
        (6, 10),
        (6, 8),
        (6, 6),
        (6, 4),
        (6, 3),
        (6, 2),
    ]

    LINE_HALF_LENGTH = 50.0   # each beam extends this far either side of its cluster center
    CLUSTER_SPACING  = 200.0  # distance between cluster centers — large enough that
                               # no beam from one cluster can reach another cluster's center
    GRID_WIDTH = 10            # number of cluster columns before wrapping to a new row

    lines        = []
    cluster_info = []

    for cluster_idx, (n_clusters, n_lines) in enumerate(
        (spec for n_clusters, n_lines in cluster_specs for spec in [(n_clusters, n_lines)] * 1)
    ):
        pass  # replaced below — see real loop

    # Real loop: flatten cluster_specs into one cluster at a time
    flat_specs = [
        n_lines
        for n_clusters, n_lines in cluster_specs
        for _ in range(n_clusters)
    ]

    for cluster_idx, n_lines in enumerate(flat_specs):

        # --------------------------------------------------------------
        # Place cluster centers on a regular 2D grid in the XY plane.
        # Wrapping every GRID_WIDTH columns keeps the layout readable.
        # --------------------------------------------------------------
        row = cluster_idx // GRID_WIDTH
        col = cluster_idx  % GRID_WIDTH
        center = Point(col * CLUSTER_SPACING, row * CLUSTER_SPACING, 0.0)
        cluster_info.append((center, n_lines))

        for _ in range(n_lines):

            # ----------------------------------------------------------
            # Sample a uniformly random direction on the unit sphere.
            # Using acos(uniform(-1, 1)) for the polar angle gives true
            # uniformity — the simpler uniform(0, pi) would over-sample
            # near the poles.
            # ----------------------------------------------------------
            theta = math.acos(rng.uniform(-1.0, 1.0))  # polar angle    [0, π]
            phi   = rng.uniform(0.0, 2.0 * math.pi)    # azimuthal angle [0, 2π]

            dx = math.sin(theta) * math.cos(phi)
            dy = math.sin(theta) * math.sin(phi)
            dz = math.cos(theta)

            # ----------------------------------------------------------
            # Optionally perturb this line's individual pass-through
            # point. Each line in the cluster gets its own small offset,
            # so pairwise joints land near but not exactly on the center.
            # Set jitter=0.0 to keep intersections perfectly exact.
            # ----------------------------------------------------------
            px = center.x + rng.uniform(-jitter, jitter)
            py = center.y + rng.uniform(-jitter, jitter)
            pz = center.z + rng.uniform(-jitter, jitter)

            # Build the line by extending the direction vector equally
            # in both directions from the (possibly jittered) pass-through point.
            start = Point(px - dx * LINE_HALF_LENGTH,
                          py - dy * LINE_HALF_LENGTH,
                          pz - dz * LINE_HALF_LENGTH)

            end   = Point(px + dx * LINE_HALF_LENGTH,
                          py + dy * LINE_HALF_LENGTH,
                          pz + dz * LINE_HALF_LENGTH)

            lines.append(Line(start, end))

    return lines, cluster_info
 

def make_model(lines):
    model = TimberModel()

    WIDTH, HEIGHT = 0.08, 0.10
    for line in lines:
        model.add_element(Beam.from_centerline(line, width=WIDTH, height=HEIGHT))

    model.connect_adjacent_beams(max_distance=0.02)
    return model

def get_cluster_counts(clusters):
    """Group clusters by their element count and return an OrderedDict
    sorted by the count (the keys).

    Parameters
    ----------
    clusters : iterable
        Iterable of cluster objects with a length accessible via ``len(c.elements)``.

    Returns
    -------
    OrderedDict
        Mapping from count -> list[cluster], sorted by count.
    """
    output = OrderedDict()

    for c in clusters:
        count = len(c.elements)
        output.setdefault(count, []).append(c)

    od = OrderedDict(sorted(output.items()))
    for count, clusters in od.items():
        print(f"{len(clusters)} clusters found with {count} elements")

    return ([len(clusters) for clusters in od.values()])

def print_cluster_info(cluster):
    output = {}

    for c in cluster:
        count = len(c.elements)
        if not output.get(count):
            output[count]=[]
        output[count].append(c)


    for k, v in output.items():
        print(f"{len(v)} clusters found with {k} elements")


def main():
    results = []

    other_results = find_all_clusters(make_model(beams()[0]).joint_candidates, max_distance=0.02)
    print("expected results:")
    print_cluster_info(other_results)
    print("--------------------------------------------------------------------")


    for _ in range(4):
        lines = beams()[0]
        model = make_model(lines)

        # Test just pairs

        analyzer = MaxNCompositeAnalyzer(model, n=5)
        clusters = analyzer.find()

        results.append(get_cluster_counts(clusters))

        print("--------------------------------------------------------------------")

    other_results = find_all_clusters(model.joint_candidates, max_distance=0.02)
    print("results:")
    for r in results:
        print(f"{r}")

    assert all([results[0]==r for r in results[1:]]), "Results differ across runs — this should not happen!"


if __name__ == "__main__":
    main()

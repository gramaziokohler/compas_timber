"""This is a benchmarking script which was used to figure out performance bottlenecks in Cluster analysis."""

from time import time
import random
import math

from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import get_clusters_from_model
from compas_timber.elements import Beam
from compas_timber.model import TimberModel



def beams_clusters(cluster_count, seed=42, jitter=0.0):
    """Generate beam centerlines arranged in clusters of known sizes.

    Each cluster is a group of lines whose centerlines all pass through
    (or very near) the same point. When pairwise joints are computed from
    these beams, all joints within a cluster will share approximately the
    same location — exactly what the clustering algorithm needs to find.

    Parameters
    ----------
    cluster_count : int
        Number of each size cluster to generate. 
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
    start = time()

    WIDTH, HEIGHT = 0.08, 0.10
    for line in lines:
        model.add_element(Beam.from_centerline(line, width=WIDTH, height=HEIGHT))
    print(f"    Time taken to generate beams and model: {time() - start}")


    start = time()

    model.connect_adjacent_beams(max_distance=0.02)
    print(f"    Time taken to find joint candidates: {time() - start}")
    return model

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
    # ballpark execution times:
    # 7 beams - Time taken: 0.0003750324249267578
    # 26 beams - Time taken: 0.012112855911254883
    # 57 beams - Time taken: 0.1553349494934082


    for i in [1,2,4,6,8,12]:
        lines, _ = beams_clusters(i)
        print(len(lines), "beams")
        model = make_model(lines)

        # new function
        print("")
        print("get_clusters_from_model()")
        start = time()
        clusters = get_clusters_from_model(model)
        duration=time() - start
        print(f"    Time taken for get_clusters_from_model: {duration}")

        print_cluster_info(clusters)
        print("--------------------------------------------------------------------")



if __name__ == "__main__":
    main()

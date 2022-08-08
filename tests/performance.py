import copy
import time

import matplotlib.pyplot as plt
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.connections.joint import Joint
from compas_timber.connections.t_butt import TButtJoint
from compas_timber.parts.beam import Beam
from compas_timber.utils.workflow import set_defaul_joints


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if "log_time" in kw:
            name = kw.get("log_name", method.__name__.upper())
            kw["log_time"][name] = int((te - ts) * 1000)
        else:
            print("%r  %2.2f ms" % (method.__name__, (te - ts) * 1000))
        return result

    return timed


@timeit
def large_assembly(size=100):
    t0 = time.time()
    n = size - 2
    w = 0.1
    h = 0.16
    d = 0.5
    y = 3.0
    v = Vector(0,0,1)
    beams = []
    for i in range(n):
        # make studs
        x = i * d
        beam = Beam.from_endpoints(Point(x, 0, 0), Point(x, y, 0), v, width=w, height=h)
        beams.append(beam)

    # make sleepers
    beams.append(
        Beam.from_endpoints(Point(0, 0, 0), Point(d * n, 0, 0), v, width=w, height=h)
    )
    beams.append(
        Beam.from_endpoints(Point(0, y, 0), Point(d * n, y, 0), v, width=w, height=h)
    )
    t1 = time.time()

    A = TimberAssembly()
    for b in beams:
        A.add_beam(b)
    #print(A.find(beams[0]))

    t2 = time.time()
    # set_defaul_joints(A) #-> ca 9s for 500 beams
    for i in range(n):
        TButtJoint(A, beams[i], beams[n])
        TButtJoint(A, beams[i], beams[n + 1])

    t3 = time.time()
    return [t0, t1, t2, t3]


if __name__ == "__main__":

    model_sizes = []
    exec_times = []

    for i in range(10):
        s = i * 100
        # ts = time.time()
        t = large_assembly(s)
        # te = time.time()
        # t = (te-ts)*1000

        model_sizes.append(s)
        exec_times.append(t)

    print(exec_times)
    plt.plot(
        model_sizes,
        [(t1 - t0) * 1000 for t0, t1, t2, t3 in exec_times],
        "b",
        label="create beams",
    )
    plt.plot(
        model_sizes,
        [(t2 - t1) * 1000 for t0, t1, t2, t3 in exec_times],
        "g",
        label="add beams to assembly",
    )
    plt.plot(
        model_sizes,
        [(t3 - t2) * 1000 for t0, t1, t2, t3 in exec_times],
        "r",
        label="create joints explicitly",
    )
    plt.xlabel("no of beams")
    plt.ylabel("[ms]")
    plt.legend(loc="upper left")
    plt.show()

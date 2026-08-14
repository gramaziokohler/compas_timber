"""Kinematic assembly sequencing.

Produces an assembly order for a set of jointed elements, a per-element unit insertion
vector for trajectory planning, and an explicit set of elements that must be placed by
hand.

Three consumers, in priority order:

1. **Robotic assembly** -- `compas_fab` consumes the unit insertion vector. The approach
   distance is fixed, short, and decided downstream.
2. **Visualization** -- display of order and direction.
3. **Human fabrication** -- the hand-placement set is a real fabrication instruction.

The tool must work acceptably on all designs and let the user override both the order and
the hand-placement set. Every design has exceptions; the job is to get close and make the
exceptions easy to express, not to be right unaided.

Packaging
---------
This is a second top-level package shipped in the ``compas_timber`` wheel, at the same
version, from the same repository. That is deliberate and temporary: the intent is to
split it into its own distribution once it is stable. It is a sibling of
``compas_timber`` rather than a submodule so that the dependency direction is enforced
structurally -- ``compas_timber`` imports this package, and because that reverse
dependency already exists, any import back would be circular. The boundary defends
itself.

Dependencies are ``compas.geometry`` and the standard library. No numpy, no scipy: the
solver is dot products and cross products. Python 3.9 syntax throughout, because this
must run under Rhino's CPython.

Everything the algorithms are permitted to know about a model passes through
:class:`~assembly_sequencing.boundary.SequencingInput`. ``compas_timber`` supplies the
adapter that builds one from a ``TimberModel``; constraint *computation* stays on the
joint classes where the joint's private geometry lives, and only *consumption* lives here.

Known limitations, accepted
---------------------------
* **Cone feasibility is infinitesimal freedom.** ``min_i(n_i . d) > 0`` says the element
  can *begin* to move, not that it can travel far enough to clear the assembly. The
  swept broad-phase check mitigates this over the fixed approach distance; it does not
  eliminate the gap for deep mortises, scarfs or long engagements.
* **No clearance distance.** Maximum travel before collision is expensive and the
  approach distance is fixed and short downstream, so it is deliberately not computed.
* **The robot is not a point.** Gripper and arm collision with already-placed elements is
  `compas_fab`'s domain. A sequence certified here can still be unbuildable for reach
  reasons.
* **Monotone sequences only.** No assemble, disassemble, reassemble.

Examples
--------
>>> from compas.geometry import Vector
>>> from assembly_sequencing import HalfSpace, SequencingInput, generate
>>> ids = ["post", "beam"]
>>> constraints = {
...     ("post", frozenset(["beam"])): [HalfSpace(Vector(0, 0, -1))],
...     ("beam", frozenset(["post"])): [HalfSpace(Vector(0, 0, 1))],
... }
>>> data = SequencingInput(
...     element_ids=ids,
...     neighbors={"post": {"beam"}, "beam": {"post"}},
...     base_z={"post": 0.0, "beam": 1.0},
...     centroid_z={"post": 0.5, "beam": 1.0},
...     length={"post": 1.0, "beam": 2.0},
...     constraints=lambda i, active: constraints.get((i, frozenset(active)), []),
... )
>>> generate(data).order
['post', 'beam']

"""

from .blocking import build_blocking_graph
from .blocking import disconnecting_elements
from .blocking import extract
from .blocking import fully_blocked
from .blocking import ground_ids
from .blocking import intrinsic_locks
from .blocking import order_dependent_locks
from .blocking import strongly_connected_components
from .blocking import subassemblies
from .boundary import SequencingInput
from .boundary import sort_key
from .constraints import TOL
from .constraints import Constraint
from .constraints import HalfSpace
from .constraints import SignedAxis
from .constraints import validate_constraints
from .preferences import GravityStrategy
from .preferences import HeuristicStrategy
from .preferences import PreferenceStrategy
from .preferences import RankingContext
from .result import LOCKED
from .result import ROOMY
from .result import TIGHT
from .result import Locked
from .result import PinConflict
from .result import SequenceResult
from .result import Solution
from .result import StalenessReport
from .result import StuckReport
from .search import DEFAULT_BEAM_WIDTH
from .search import beam_search
from .search import generate
from .solver import APPROACH_DISTANCE
from .solver import PARALLEL_TOL
from .solver import ROOMY_MARGIN
from .solver import candidate_directions
from .solver import classify
from .solver import rank_candidates
from .solver import solve
from .trace import get_tracer
from .trace import set_tracer
from .trace import trace
from .trace import tracing

__version__ = "2.1.2"

__all__ = [
    "APPROACH_DISTANCE",
    "Constraint",
    "DEFAULT_BEAM_WIDTH",
    "GravityStrategy",
    "HalfSpace",
    "HeuristicStrategy",
    "LOCKED",
    "Locked",
    "PARALLEL_TOL",
    "PinConflict",
    "PreferenceStrategy",
    "ROOMY",
    "ROOMY_MARGIN",
    "RankingContext",
    "SequenceResult",
    "SequencingInput",
    "SignedAxis",
    "Solution",
    "StalenessReport",
    "StuckReport",
    "TIGHT",
    "TOL",
    "beam_search",
    "build_blocking_graph",
    "candidate_directions",
    "classify",
    "disconnecting_elements",
    "extract",
    "fully_blocked",
    "generate",
    "get_tracer",
    "ground_ids",
    "intrinsic_locks",
    "order_dependent_locks",
    "rank_candidates",
    "set_tracer",
    "solve",
    "sort_key",
    "strongly_connected_components",
    "subassemblies",
    "trace",
    "tracing",
    "validate_constraints",
]

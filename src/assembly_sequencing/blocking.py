"""Blocking relations over the complete model.

Two questions are answered here, and they are not the same question:

* Which elements are locked **in every order** -- intrinsic locks. These are the only
  results that legitimately mean "place by hand". They are found once, up front, as the
  strongly connected components of the blocking graph.
* Which elements are locked **given what is still in place** -- order-dependent locks.
  Those are a property of a search state, not of the design, and the search routes
  around them. They must never reach a shop floor as a fabrication instruction.

This is a reduced form of Wilson & Latombe's non-directional blocking graph (~1994). The
full sphere partition is not implemented; an SCC pass over a single blocking relation
gives what is needed here for a fraction of the work. The full NDBG is the road if
subassembly-level sequencing is wanted later.

"""

from .boundary import sort_key
from .result import Locked
from .solver import APPROACH_DISTANCE
from .solver import solve


def extract(sequencing_input, element_id, active_ids, distance=APPROACH_DISTANCE):
    """Solve the extraction of one element from one state.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    element_id : hashable
        The element to extract. Must be in `active_ids`.
    active_ids : set
        Every element still in place, including `element_id` itself.
    distance : float, optional
        Swept-check approach distance.

    Returns
    -------
    :class:`~assembly_sequencing.result.Solution` or :class:`~assembly_sequencing.result.Locked`

    """
    active = set(active_ids)
    neighbors = sequencing_input.active_neighbors(element_id, active)
    constraints = sequencing_input.constraints(element_id, neighbors)

    others = active - {element_id}

    def path_check(direction):
        return sequencing_input.path_is_clear(element_id, direction, distance, others)

    return solve(constraints, path_check if sequencing_input.has_geometry else None)


def build_blocking_graph(sequencing_input, active_ids=None, distance=APPROACH_DISTANCE):
    """Directed graph where ``A -> B`` means "B must be removed before A, whatever the order".

    The edge test is deliberately **pairwise**: an edge exists when the joint between A
    and B locks A *on its own*, with every other element already gone. That makes the
    edge an unconditional precedence -- if B alone locks A, no order can take A out while
    B is there.

    The tempting stronger rule -- draw an edge to every neighbour that participates in
    locking A in the complete assembly -- is unsound. Blocking is disjunctive: an element
    freed by removing *either* B *or* C would get edges to both, turning an OR into an
    AND and inventing cycles where a perfectly good order exists.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    active_ids : set, optional
        Defaults to the complete model.
    distance : float, optional

    Returns
    -------
    dict
        Maps element id -> set of blocker ids. Every active id is a key.

    """
    active = set(sequencing_input.element_ids) if active_ids is None else set(active_ids)
    graph = {element_id: set() for element_id in active}

    for element_id in sorted(active, key=sort_key):
        blockers = set()
        for neighbor_id in sorted(sequencing_input.active_neighbors(element_id, active), key=sort_key):
            pair = {element_id, neighbor_id}
            if not extract(sequencing_input, element_id, pair, distance).is_feasible:
                blockers.add(neighbor_id)
        graph[element_id] = blockers

    return graph


def fully_blocked(sequencing_input, active_ids=None, distance=APPROACH_DISTANCE):
    """Elements that cannot be extracted from the complete assembly.

    These are *candidates* for hand placement, not proof of one: an element locked with
    every neighbour in place may well come free once a neighbour is removed. Proof is
    :func:`intrinsic_locks`.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    active_ids : set, optional
    distance : float, optional

    Returns
    -------
    dict
        Maps element id -> the :class:`~assembly_sequencing.result.Locked` result.

    """
    active = set(sequencing_input.element_ids) if active_ids is None else set(active_ids)
    blocked = {}
    for element_id in sorted(active, key=sort_key):
        result = extract(sequencing_input, element_id, active, distance)
        if not result.is_feasible:
            blocked[element_id] = result
    return blocked


def strongly_connected_components(graph):
    """Tarjan's SCC algorithm, iterative.

    Iterative rather than recursive so that a deep model does not hit Python's recursion
    limit, which Rhino's CPython shares.

    Parameters
    ----------
    graph : dict
        Maps node -> iterable of successor nodes.

    Returns
    -------
    list of list
        Each component's members, sorted; components sorted by their first member. Both
        orderings are derived from the ids alone, so two runs on identical input give
        identical labels.

    """
    index_of = {}
    low_of = {}
    on_stack = set()
    stack = []
    components = []
    counter = [0]

    for root in sorted(graph.keys(), key=sort_key):
        if root in index_of:
            continue

        work = [(root, iter(sorted(graph.get(root, ()), key=sort_key)))]
        index_of[root] = low_of[root] = counter[0]
        counter[0] += 1
        stack.append(root)
        on_stack.add(root)

        while work:
            node, successors = work[-1]
            advanced = False
            for successor in successors:
                if successor not in graph:
                    continue
                if successor not in index_of:
                    index_of[successor] = low_of[successor] = counter[0]
                    counter[0] += 1
                    stack.append(successor)
                    on_stack.add(successor)
                    work.append((successor, iter(sorted(graph.get(successor, ()), key=sort_key))))
                    advanced = True
                    break
                if successor in on_stack:
                    low_of[node] = min(low_of[node], index_of[successor])
            if advanced:
                continue

            work.pop()
            if work:
                parent = work[-1][0]
                low_of[parent] = min(low_of[parent], low_of[node])

            if low_of[node] == index_of[node]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(sorted(component, key=sort_key))

    components.sort(key=lambda component: sort_key(component[0]))
    return components


def intrinsic_locks(graph):
    """Mutually blocking clusters: locked in every order.

    Parameters
    ----------
    graph : dict
        A blocking graph from :func:`build_blocking_graph`.

    Returns
    -------
    list of frozenset
        Components of size greater than one. Each member blocks, transitively, something
        that blocks it back, so no member can go first and no order exists that frees
        them.

    Notes
    -----
    Sound but not complete. Every cluster reported here really is locked in every order,
    because every edge is an unconditional pairwise precedence. But an interlock that only
    closes across three or more elements at once -- each pair separable, the trio not --
    has no pairwise edge to find, so it is not reported here. Those surface as a
    :class:`~assembly_sequencing.result.StuckReport` from the search instead, which is the
    honest outcome: the tool did not find an order, rather than claiming none exists.

    """
    return [frozenset(component) for component in strongly_connected_components(graph) if len(component) > 1]


def subassemblies(sequencing_input, graph):
    """Assign every element a subassembly label.

    User-declared model groups always win. Where none are declared, the strongly
    connected components of the blocking graph supply real, geometry-derived groups; an
    element in no cluster is its own subassembly.

    Labels are derived from element ids, never from iteration order, so two runs on
    identical input produce identical labels. The label propagation this replaces broke
    ties on ``(count, guid)``, and since guids are random the labels -- and therefore the
    whole ranking -- differed between runs on identical input.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    graph : dict
        A blocking graph from :func:`build_blocking_graph`.

    Returns
    -------
    dict
        Maps element id -> label.

    """
    labels = {}
    for component in strongly_connected_components(graph):
        label = component[0]
        for member in component:
            labels[member] = label

    for element_id in sequencing_input.element_ids:
        if element_id in sequencing_input.groups:
            labels[element_id] = sequencing_input.groups[element_id]
        elif element_id not in labels:
            labels[element_id] = element_id

    return labels


def ground_ids(sequencing_input, active_ids=None, tolerance=1e-3):
    """The elements resting at the lowest level of the assembly.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    active_ids : set, optional
    tolerance : float, optional

    Returns
    -------
    set

    """
    active = set(sequencing_input.element_ids) if active_ids is None else set(active_ids)
    if not active:
        return set()
    lowest = min(sequencing_input.base_z[element_id] for element_id in active)
    return set(element_id for element_id in active if sequencing_input.base_z[element_id] <= lowest + tolerance)


def disconnecting_elements(sequencing_input, active_ids, grounded_ids):
    """Elements whose removal would strand part of the assembly from the ground.

    One Tarjan articulation-point pass answers this for every candidate at once in
    O(V+E), replacing a full BFS per candidate per step.

    What this measures is *connectivity to a lowest-level element*, which is a
    topological proxy and not a stability criterion. A piece that stays connected can
    still tip over, and a piece that disconnects may be perfectly happy on the ground.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    active_ids : set
    grounded_ids : set
        The elements that count as supported, typically from :func:`ground_ids`.

    Returns
    -------
    set
        Element ids whose removal would leave a non-empty component with no grounded
        member. A component that is *already* ungrounded is not counted: removal did not
        create that.

    """
    active = set(active_ids)
    grounded = set(grounded_ids) & active
    adjacency = {node: sorted(sequencing_input.neighbors[node] & active, key=sort_key) for node in active}

    disc = {}
    low = {}
    parent = {}
    subtree_size = {}
    subtree_ground = {}
    separated = {node: [] for node in active}
    counter = [0]
    result = set()

    for root in sorted(active, key=sort_key):
        if root in disc:
            continue

        component = []
        root_children = []
        work = [(root, iter(adjacency[root]))]
        disc[root] = low[root] = counter[0]
        counter[0] += 1
        parent[root] = None
        subtree_size[root] = 1
        subtree_ground[root] = 1 if root in grounded else 0
        component.append(root)

        while work:
            node, neighbors = work[-1]
            advanced = False
            for neighbor in neighbors:
                if neighbor not in disc:
                    disc[neighbor] = low[neighbor] = counter[0]
                    counter[0] += 1
                    parent[neighbor] = node
                    subtree_size[neighbor] = 1
                    subtree_ground[neighbor] = 1 if neighbor in grounded else 0
                    component.append(neighbor)
                    if node == root:
                        root_children.append(neighbor)
                    work.append((neighbor, iter(adjacency[neighbor])))
                    advanced = True
                    break
                if neighbor != parent[node]:
                    low[node] = min(low[node], disc[neighbor])
            if advanced:
                continue

            work.pop()
            if work:
                above = work[-1][0]
                low[above] = min(low[above], low[node])
                subtree_size[above] += subtree_size[node]
                subtree_ground[above] += subtree_ground[node]
                if above != root and low[node] >= disc[above]:
                    separated[above].append((subtree_size[node], subtree_ground[node]))

        # Removing the DFS root splits off each of its child subtrees.
        for child in root_children:
            separated[root].append((subtree_size[child], subtree_ground[child]))

        total_size = len(component)
        total_ground = sum(1 for node in component if node in grounded)
        if total_ground == 0:
            # Already ungrounded; nothing a removal does here *creates* the condition.
            continue

        for node in component:
            parts = separated[node]
            if any(ground == 0 for _, ground in parts):
                result.add(node)
                continue
            # What is left over once the split-off subtrees are accounted for. A node that
            # is not an articulation point has no subtrees, and the remainder is simply
            # everything else -- which still matters when the node was the only grounded
            # element in its component.
            remainder_size = total_size - 1 - sum(size for size, _ in parts)
            remainder_ground = total_ground - (1 if node in grounded else 0) - sum(ground for _, ground in parts)
            if remainder_size > 0 and remainder_ground == 0:
                result.add(node)

    return result


def order_dependent_locks(sequencing_input, active_ids, intrinsic, distance=APPROACH_DISTANCE):
    """Locked elements in a given state that are *not* intrinsically locked.

    Provided so callers can keep the two failures apart in reporting, which is the whole
    point of splitting them.

    Parameters
    ----------
    sequencing_input : :class:`~assembly_sequencing.boundary.SequencingInput`
    active_ids : set
    intrinsic : iterable of frozenset
        The clusters from :func:`intrinsic_locks`.
    distance : float, optional

    Returns
    -------
    dict
        Maps element id -> :class:`~assembly_sequencing.result.Locked`.

    """
    locked_members = set()
    for cluster in intrinsic:
        locked_members |= set(cluster)

    out = {}
    for element_id in sorted(set(active_ids), key=sort_key):
        if element_id in locked_members:
            continue
        result = extract(sequencing_input, element_id, active_ids, distance)
        if isinstance(result, Locked):
            out[element_id] = result
    return out

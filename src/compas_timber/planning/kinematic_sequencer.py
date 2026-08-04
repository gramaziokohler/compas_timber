from compas.geometry import Vector
from compas_timber.planning.insertion_solver import InsertionSolver


class KinematicSequenceGenerator(object):
    """Generates an assembly sequence by checking kinematic escape constraints.
    
    The algorithm uses Disassembly Planning: it works backwards from the completed 
    model and attempts to greedily "pull" elements out one by one. Once the full 
    disassembly sequence is found, it is reversed to yield the assembly sequence.
    
    Parameters
    ----------
    model : :class:`~compas_timber.model.TimberModel`
        Model to be sequenced.
    heuristic : callable, optional
        A function to evaluate elements and guide the sequence. Elements with 
        higher heuristic scores are prioritized. Example: `lambda e: e.frame.point.z`
    """

    def __init__(self, model, heuristic=None):
        self.model = model
        self.solver = InsertionSolver(model)
        self.heuristic = heuristic
        self.topological_levels = {}
        self.precedence_graph = {}
        self.subassemblies = {}

    def _get_element_z(self, element):
        """Helper to calculate the effective Z height of an element."""
        if hasattr(element, 'centerline') and element.centerline:
            return min(element.centerline.start.z, element.centerline.end.z) + element.centerline.midpoint.z
        elif hasattr(element, 'obb') and element.obb:
            return element.obb.frame.point.z
        else:
            return 0.0

    def _compute_topological_levels(self, elements):
        """Computes the topological distance of each element from the ground using BFS."""
        self.topological_levels = {}
        if not elements:
            return
            
        # 1. Find the absolute lowest physical Z coordinate in the model
        min_z = min(self._get_element_z(e) for e in elements)
        
        # 2. Identify 'Support' elements (Level 0)
        queue = []
        visited = set()
        for e in elements:
            lowest_z = self._get_element_z(e) 
            if hasattr(e, 'centerline') and e.centerline:
                lowest_z = min(e.centerline.start.z, e.centerline.end.z)
            if lowest_z <= min_z + 1e-3:
                self.topological_levels[e.guid] = 0
                queue.append((e, 0))
                visited.add(e.guid)
                
        # 3. BFS to assign levels based on actual structural joints
        while queue:
            current_element, current_level = queue.pop(0)
            joints = self.model.get_joints_for_element(current_element)
            for joint in joints:
                for neighbor in joint.elements:
                    if neighbor.guid not in visited:
                        visited.add(neighbor.guid)
                        self.topological_levels[neighbor.guid] = current_level + 1
                        queue.append((neighbor, current_level + 1))
                        
        # 4. Fallback for any disconnected elements
        for e in elements:
            if e.guid not in visited:
                self.topological_levels[e.guid] = 999

    def _build_precedence_graph(self, elements):
        """Builds a directed graph where edge A -> B means A MUST be assembled before B."""
        self.precedence_graph = {e.guid: set() for e in elements}
        element_set = {e.guid for e in elements}
        
        for joint in self.model.joints:
            j_elements = joint.elements
            if len(j_elements) == 2:
                a, b = j_elements
                if a.guid not in element_set or b.guid not in element_set:
                    continue
                    
                # Check if A can be extracted from B
                vec_a = self.solver.get_extraction_vector(a, [joint])
                # Check if B can be extracted from A
                vec_b = self.solver.get_extraction_vector(b, [joint])
                
                if vec_a is None and vec_b is not None:
                    # A cannot be extracted if B is present, but B can.
                    # B must be disassembled before A. In assembly, A before B.
                    self.precedence_graph[a.guid].add(b.guid)
                elif vec_b is None and vec_a is not None:
                    self.precedence_graph[b.guid].add(a.guid)

    def _detect_subassemblies(self, elements):
        """Uses Label Propagation to cluster elements into subassemblies."""
        labels = {e.guid: e.guid for e in elements}
        element_set = {e.guid for e in elements}
        
        # Build adjacency list
        adj = {e.guid: [] for e in elements}
        for e in elements:
            joints = self.model.get_joints_for_element(e)
            for j in joints:
                for other in j.elements:
                    if other.guid != e.guid and other.guid in element_set:
                        adj[e.guid].append(other.guid)
                        
        # Propagate labels
        for _ in range(10): # max 10 iterations
            changed = False
            for node, neighbors in adj.items():
                if not neighbors:
                    continue
                counts = {}
                for nbr in neighbors:
                    lbl = labels[nbr]
                    counts[lbl] = counts.get(lbl, 0) + 1
                
                best_label = max(counts.items(), key=lambda x: (x[1], x[0]))[0]
                if labels[node] != best_label:
                    labels[node] = best_label
                    changed = True
            if not changed:
                break
                
        # Group by label
        self.subassemblies = labels

    def _creates_floating_component(self, candidate, remaining_set):
        """Checks if removing candidate from remaining_set creates a floating disconnected component."""
        nodes = remaining_set - {candidate.guid}
        if not nodes:
            return False
            
        visited = set()
        
        def bfs_is_supported(start_guid):
            queue = [start_guid]
            component_visited = set()
            has_support = False
            
            while queue:
                curr = queue.pop(0)
                if curr not in component_visited:
                    component_visited.add(curr)
                    visited.add(curr)
                    
                    if self.topological_levels.get(curr, 999) == 0:
                        has_support = True
                        
                    element = self.model.get_element(curr)
                    if element is None: continue
                    joints = self.model.get_joints_for_element(element)
                    for j in joints:
                        for other in j.elements:
                            if other.guid in nodes and other.guid not in component_visited:
                                queue.append(other.guid)
                                
            return has_support

        for node in nodes:
            if node not in visited:
                is_supported = bfs_is_supported(node)
                if not is_supported:
                    return True # Found a floating component!
                    
        return False

    def _evaluate_candidate(self, element, active_joints, last_disassembled, remaining_elements, remaining_set):
        """Scores a candidate using strict Lexicographical Tuple scoring."""
        # Precedence check (A -> B means A must be assembled before B, so B must be disassembled before A).
        # We are considering disassembling `element`. If `element` must be assembled BEFORE some `other` element still in remaining_set,
        # then we CANNOT disassemble `element` yet, because `other` must be disassembled first.
        # Check edges: element -> other
        is_precedence_valid = True
        for other_guid in self.precedence_graph.get(element.guid, set()):
            if other_guid in remaining_set:
                is_precedence_valid = False
                break
                
        element_z = self._get_element_z(element)
        
        # Priority 1: Strict Local Z-Dependency (MUST NOT have connected higher beams)
        is_local_z_valid = True
        for joint in active_joints:
            for other in joint.elements:
                if other.guid != element.guid and other.guid in remaining_set:
                    if self._get_element_z(other) > element_z + 1e-3:
                        is_local_z_valid = False
                        break
            if not is_local_z_valid:
                break
                
        # Priority 2: Floating components (Stability)
        creates_floating = self._creates_floating_component(element, remaining_set)
        is_stable_globally = not creates_floating
        
        # Subassembly alignment: try to disassemble elements of the same subassembly together
        same_subassembly = False
        if last_disassembled is not None:
            if self.subassemblies.get(element.guid) == self.subassemblies.get(last_disassembled.guid):
                same_subassembly = True

        # Priority 3: Physical Z Height (Highest first, absolutely)
        z_height = element_z
        
        # Priority 4: Topological Graph Level
        topo_level = self.topological_levels.get(element.guid, 999)
        
        # Priority 5: Building Chain Continuity
        is_in_chain = False
        if last_disassembled is not None:
            u, v = element.graphnode, last_disassembled.graphnode
            if self.model._graph.has_edge((u, v)) or self.model._graph.has_edge((v, u)):
                is_in_chain = True
                
        # Priority 6: Element Length
        length = element.centerline.length if hasattr(element, 'centerline') and element.centerline else 0
        
        # Priority 7: Centrality (Penalize highly connected core elements)
        total_joints = len(self.model.get_joints_for_element(element))
        
        # Return strict hierarchy tuple. Python sorts element-by-element natively.
        return (
            int(is_precedence_valid), # MUST be true to respect kinematic DAG
            int(is_stable_globally),  # MUST be true to prevent parts falling off
            int(is_local_z_valid),
            int(same_subassembly),    # Group by subassemblies
            z_height,
            topo_level,
            int(is_in_chain),
            length,
            -total_joints
        )

    def generate(self):
        """Generates the assembly sequence and writes the data into the model graph and element attributes."""
        # Sequence all elements, not just beams (or fallback to beams if none)
        elements = list(self.model.elements())
        if not elements:
            elements = list(self.model.beams)
            
        self._compute_topological_levels(elements)
        self._build_precedence_graph(elements)
        self._detect_subassemblies(elements)
        
        remaining_elements = elements[:]
        disassembly_sequence = []
        extraction_vectors = []
        
        # Quick lookup for active elements
        remaining_set = set(e.guid for e in remaining_elements)
        last_disassembled = None
        
        while remaining_elements:
            # Score and sort all remaining elements so the absolute "best" (highest) comes first
            if self.heuristic:
                remaining_elements.sort(key=self.heuristic, reverse=True)
            else:
                remaining_elements.sort(
                    key=lambda e: self._evaluate_candidate(
                        e, 
                        [j for j in self.model.get_joints_for_element(e) if any(o.guid in remaining_set for o in j.elements if o.guid != e.guid)], 
                        last_disassembled,
                        remaining_elements,
                        remaining_set
                    ),
                    reverse=True
                )
            
            # The strictly highest scoring element according to our rules
            best_element = remaining_elements[0]
            
            # Now we figure out if it can be extracted cleanly, or if it must be forced
            active_joints = [j for j in self.model.get_joints_for_element(best_element) if any(o.guid in remaining_set for o in j.elements if o.guid != best_element.guid)]
            
            if not active_joints:
                # Totally free
                escape_vector = Vector(0, 0, 1)
            else:
                escape_vector = self.solver.get_extraction_vector(best_element, active_joints)
                
            if escape_vector is None:
                import logging
                logging.warning(f"Kinematic deadlock for element {best_element.name} ({best_element.guid}). Forcefully extracting (must be placed by hand).")
                
            # Record and remove the element
            disassembly_sequence.append(best_element)
            extraction_vectors.append(escape_vector)
            last_disassembled = best_element
            
            remaining_elements.remove(best_element)
            remaining_set.remove(best_element.guid)
            
        # Reverse the disassembly sequence to get the assembly sequence
        assembly_sequence = list(reversed(disassembly_sequence))
        
        # Reverse the extraction vectors to get insertion vectors
        insertion_vectors = []
        for v in reversed(extraction_vectors):
            if v is not None:
                insertion_vectors.append(-v)
            else:
                insertion_vectors.append(None)
                
        # Write sequence data to both the TimberModel graph and directly on the element attributes
        for i, element in enumerate(assembly_sequence):
            node = element.graphnode
            vector = insertion_vectors[i]
            is_manual = vector is None
            
            # Graph Attributes
            self.model._graph.node_attribute(node, 'assembly_sequence', value=i)
            self.model._graph.node_attribute(node, 'insertion_vector', value=vector)
            self.model._graph.node_attribute(node, 'requires_manual_assembly', value=is_manual)
            
            # Element Attributes
            element.attributes['assembly_sequence'] = i
            element.attributes['insertion_vector'] = vector
            element.attributes['requires_manual_assembly'] = is_manual

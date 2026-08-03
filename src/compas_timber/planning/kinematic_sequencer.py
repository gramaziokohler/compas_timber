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

    def _get_element_z(self, element):
        """Helper to calculate the effective Z height of an element."""
        # return element.centerline.midpoint.z + element.centerline.start.z + element.centerline.end.z
        return min(element.centerline.start.z, element.centerline.end.z) + element.centerline.midpoint.z

    def _compute_topological_levels(self):
        """Computes the topological distance of each element from the ground using BFS."""
        self.topological_levels = {}
        
        # 1. Find the absolute lowest physical Z coordinate in the model
        min_z = min(min(e.centerline.start.z, e.centerline.end.z) + e.centerline.midpoint.z for e in self.model.beams)
        
        # 2. Identify 'Support' elements (Level 0)
        queue = []
        visited = set()
        for e in self.model.beams:
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
        for e in self.model.beams:
            if e.guid not in visited:
                self.topological_levels[e.guid] = 999

    def _evaluate_candidate(self, element, active_joints, last_disassembled, remaining_elements, remaining_set):
        """Scores a candidate using strict Lexicographical Tuple scoring."""
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
        # Priority 2: Physical Z Height (Highest first, absolutely)
        z_height = element_z
        
        # Priority 3: Topological Graph Level
        topo_level = self.topological_levels.get(element.guid, 999)
        
        # Priority 4: Stability (>= 2 supports)
        stability = len(active_joints) >= 2
        
        # Priority 5: Building Chain Continuity
        is_in_chain = False
        if last_disassembled is not None:
            u, v = element.graphnode, last_disassembled.graphnode
            if self.model._graph.has_edge((u, v)) or self.model._graph.has_edge((v, u)):
                is_in_chain = True
                
        # Priority 6: Beam Length (Longest early)
        length = element.centerline.length
        
        # Priority 7: Centrality (Penalize highly connected core elements)
        total_joints = len(self.model.get_joints_for_element(element))
        
        # Return strict hierarchy tuple. Python sorts element-by-element natively.
        return (
            int(is_local_z_valid),
            z_height,
            topo_level,
            int(stability),
            int(is_in_chain),
            length,
            -total_joints
        )

    def generate(self):
        """Generates the assembly sequence and writes the data into the model graph and element attributes."""
        self._compute_topological_levels()
        
        remaining_elements = list(self.model.beams)
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

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

    def __init__(self, model, heuristic=None, z_weight=10.0, constraint_weight=5.0, chain_weight=20.0, support_weight=30.0, length_weight=5.0, centrality_weight=10.0):
        self.model = model
        self.solver = InsertionSolver(model)
        self.heuristic = heuristic
        self.z_weight = z_weight
        self.constraint_weight = constraint_weight
        self.chain_weight = chain_weight
        self.support_weight = support_weight
        self.length_weight = length_weight
        self.centrality_weight = centrality_weight

    def _evaluate_candidate(self, element, active_joints, last_disassembled):
        """Scores a candidate for disassembly based on multi-factor heuristics."""
        score = 0.0
        
        # 1. Z-level: higher elements get higher score (disassembled earlier)
        score += element.centerline.midpoint.z * self.z_weight
        
        # 2. Constraints: penalize overly constrained elements (e.g. 4+ joints)
        score -= len(active_joints) * self.constraint_weight
        
        # 3. Building Chain: prefer extracting elements connected to the one we just removed
        if last_disassembled is not None:
            # Check if they share an edge in the timber model graph
            u, v = element.graphnode, last_disassembled.graphnode
            if self.model._graph.has_edge((u, v)) or self.model._graph.has_edge((v, u)):
                score += self.chain_weight
                
        # 4. Stability: explicitly reward elements that will have 2 or more connections 
        # when assembled. (In disassembly, this means they have >= 2 active joints)
        if len(active_joints) >= 2:
            score += self.support_weight
            
        # 5. Length: longer beams cause more deformation (self-weight torque), so we assemble 
        # them late (disassemble them early). We boost their score so they are pulled out sooner.
        score += element.centerline.length * self.length_weight
        
        # 6. Centrality/Periphery: elements with many TOTAL joints in the completed model
        # form the "stiff core". They should be assembled early (disassembled late).
        # We penalise them here so they stay in the structure longer during disassembly.
        total_joints = len(self.model.get_joints_for_element(element))
        score -= total_joints * self.centrality_weight
                
        return score

    def generate(self):
        """Generates the assembly sequence and writes the data into the model graph and element attributes."""
        remaining_elements = list(self.model.beams)
        disassembly_sequence = []
        extraction_vectors = []
        
        # Quick lookup for active elements
        remaining_set = set(e.guid for e in remaining_elements)
        last_disassembled = None
        
        while remaining_elements:
            free_candidates = []
            
            # Find all elements that can be extracted without collisions
            for element in remaining_elements:
                all_joints = self.model.get_joints_for_element(element)
                
                # Active joints are those connected to elements still in the remaining pool
                active_joints = []
                for joint in all_joints:
                    is_active = any(
                        other.guid in remaining_set 
                        for other in joint.elements 
                        if other.guid != element.guid
                    )
                    if is_active:
                        active_joints.append(joint)
                
                # Check kinematic constraints against active joints
                if not active_joints:
                    # If there are no constraints, the element is completely free (e.g. the last element in the sequence)
                    # We assign a default extraction vector (straight up in the Z direction).
                    escape_vector = Vector(0, 0, 1)
                else:
                    escape_vector = self.solver.get_extraction_vector(element, active_joints)
                
                if escape_vector is not None:
                    free_candidates.append((element, escape_vector, active_joints))
            
            # If no free element could be found, the structure is kinematically locked
            if not free_candidates:
                import logging
                logging.warning("Kinematic deadlock: cannot find a free element to extract. Forcefully extracting an element (must be placed by hand).")
                
                if self.heuristic:
                    remaining_elements.sort(key=self.heuristic, reverse=True)
                else:
                    remaining_elements.sort(
                        key=lambda e: self._evaluate_candidate(
                            e, 
                            [j for j in self.model.get_joints_for_element(e) if any(o.guid in remaining_set for o in j.elements if o.guid != e.guid)], 
                            last_disassembled
                        ),
                        reverse=True
                    )
                free_element = remaining_elements[0]
                free_vector = None
            else:
                # Pick the best candidate based on the heuristic
                if self.heuristic:
                    # Sort descending so the highest scoring element is first
                    free_candidates.sort(key=lambda item: self.heuristic(item[0]), reverse=True)
                else:
                    free_candidates.sort(
                        key=lambda item: self._evaluate_candidate(item[0], item[2], last_disassembled),
                        reverse=True
                    )
                
                free_element, free_vector, _ = free_candidates[0]
                
            # Record and remove the free element
            disassembly_sequence.append(free_element)
            extraction_vectors.append(free_vector)
            last_disassembled = free_element
            
            remaining_elements.remove(free_element)
            remaining_set.remove(free_element.guid)
            
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

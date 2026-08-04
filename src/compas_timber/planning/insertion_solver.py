from compas.geometry import Line
from compas.geometry import Vector


class InsertionSolver:
    def __init__(self, model):
        self.model = model
        
    def resolve_constraints(self, constraints):
        """Calculates the mathematical intersection of multiple kinematic constraints.
        
        Parameters
        ----------
        constraints : list of (Line | list[Vector] | Vector)
            The kinematic constraints from active joints.
            
        Returns
        -------
        compas.geometry.Vector | None
            The single valid escape vector, or None if kinematically locked.
        """
        lines = []
        vectors = []
        
        for c in constraints:
            if isinstance(c, Line):
                lines.append(c)
            elif isinstance(c, list):
                vectors.extend(c)
            elif isinstance(c, Vector):
                vectors.append(c)
                
        # 1. Strict 1-DOF lock
        if lines:
            base_dir = lines[0].direction.unitized()
            
            # If multiple lines exist, verify they point in the exact same direction
            for line in lines[1:]:
                dir2 = line.direction.unitized()
                if base_dir.dot(dir2) < 1 - 1e-5:
                    return None  # Conflicting extraction directions, kinematically locked
                    
            # Check the strictly defined extraction direction against all half-spaces
            d_valid = all(base_dir.dot(v) >= -1e-5 for v in vectors)
            
            if d_valid:
                return base_dir
            else:
                return None  # Pushes through solid material
                
        # 2. >= 2-DOF Intersection (Half-spaces)
        elif vectors:
            return self._find_valid_vector(vectors)
            
        # If no constraints exist, return a default vector or None. 
        # Returning None might be safer if constraints are expected.
        return None

    def _find_valid_vector(self, vectors):
        """Generates and tests candidate vectors against half-space constraints."""
        def is_valid(vec):
            if vec.length < 1e-6:
                return False
            vec = vec.unitized()
            return all(vec.dot(v) >= -1e-5 for v in vectors)

        candidates = []
        
        # 1. Preferred Z-up direction
        candidates.append(Vector(0, 0, 1))
        
        # 2. Average normal
        sum_vec = Vector(0, 0, 0)
        for v in vectors:
            sum_vec += v.unitized()
        candidates.append(sum_vec)
        
        # 3. Individual normals (pulling straight out from a joint face)
        for v in vectors:
            candidates.append(v)
            
        # 4. Cross products of pairs (edges of the constraint cone)
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                cross = vectors[i].cross(vectors[j])
                if cross.length > 1e-6:
                    candidates.append(cross)
                    candidates.append(-cross)
                    
        # 5. Orthogonal axes (handles perfectly opposing vectors)
        axes = [Vector(1, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)]
        for v in vectors:
            for axis in axes:
                cross = v.cross(axis)
                if cross.length > 1e-6:
                    candidates.append(cross)
                    candidates.append(-cross)
                    
        # Return the first candidate that satisfies all constraints
        for c in candidates:
            if is_valid(c):
                return c.unitized()
                
        return None

    def get_extraction_vector(self, element, active_joints):
        """Gets the final extraction vector for a given element."""
        constraints = [joint.get_kinematic_constraint(element) for joint in active_joints]
        return self.resolve_constraints(constraints)

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
                
        if lines:
            base_dir = lines[0].direction.unitized()
            
            for line in lines[1:]:
                dir2 = line.direction.unitized()
                if base_dir.dot(dir2) < 1 - 1e-5:
                    return None  # Conflicting extraction directions, kinematically locked
                    
            d_valid = all(base_dir.dot(v) >= -1e-5 for v in vectors)
            
            if d_valid:
                return base_dir
            else:
                return None  # Pushes through solid material
                
        elif vectors:
            return self._find_valid_vector(vectors)
            
        return None

    def _find_valid_vector(self, vectors):
        """Generates and tests candidate vectors against half-space constraints."""
        def is_valid(vec):
            if vec.length < 1e-6:
                return False
            vec = vec.unitized()
            return all(vec.dot(v) >= -1e-5 for v in vectors)

        candidates = []
        
        candidates.append(Vector(0, 0, 1))
        
        sum_vec = Vector(0, 0, 0)
        for v in vectors:
            sum_vec += v.unitized()
        candidates.append(sum_vec)
        
        for v in vectors:
            candidates.append(v)
            
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                cross = vectors[i].cross(vectors[j])
                if cross.length > 1e-6:
                    candidates.append(cross)
                    candidates.append(-cross)
                    
        axes = [Vector(1, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)]
        for v in vectors:
            for axis in axes:
                cross = v.cross(axis)
                if cross.length > 1e-6:
                    candidates.append(cross)
                    candidates.append(-cross)
                    
        for c in candidates:
            if is_valid(c):
                return c.unitized()
                
        return None

    def get_extraction_vector(self, element, active_joints):
        """Gets the final extraction vector for a given element."""
        constraints = [joint.get_kinematic_constraint(element) for joint in active_joints]
        return self.resolve_constraints(constraints)

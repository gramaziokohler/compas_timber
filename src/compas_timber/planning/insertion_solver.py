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
                
        # 2. >= 2-DOF Intersection
        elif vectors:
            # A simple heuristic is to unitize all boundary normals and sum them.
            sum_vec = Vector(0, 0, 0)
            for v in vectors:
                sum_vec += v.unitized()
                
            if sum_vec.length < 1e-6:
                return None  # Perfectly opposing constraints, locked
                
            candidate = sum_vec.unitized()
            
            # Ensure it satisfies all half-space constraints
            if all(candidate.dot(v) >= -1e-5 for v in vectors):
                return candidate
            else:
                return None
                
        # If no constraints exist, return a default vector or None. 
        # Returning None might be safer if constraints are expected.
        return None

    def get_extraction_vector(self, element, active_joints):
        """Gets the final extraction vector for a given element."""
        constraints = [joint.get_kinematic_constraint(element) for joint in active_joints]
        return self.resolve_constraints(constraints)

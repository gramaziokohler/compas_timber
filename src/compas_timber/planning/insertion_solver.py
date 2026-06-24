from compas.geometry import cross_vectors, Vector, Plane, Line

class InsertionSolver:
    def __init__(self, model):
        self.model = model
        
    def resolve_constraints(self, constraints):
        """Calculates the mathematical intersection of multiple kinematic constraints.
        
        Parameters
        ----------
        constraints : list of (Line | Plane | Vector)
        
        Returns
        -------
        compas.geometry.Vector | None
            The single valid escape vector, or None if kinematically locked.
        """
        lines = [c for c in constraints if isinstance(c, Line)]
        planes = [c for c in constraints if isinstance(c, Plane)]
        vectors = [c for c in constraints if isinstance(c, Vector)]
        
        candidate_vector = None
        
        # 1. Strict 1-DOF lock
        if len(lines) > 0:
            # If multiple lines exist, they MUST be parallel, otherwise it's locked
            candidate_vector = lines[0].direction
            
        # 2. Planar 2-DOF Intersection
        elif len(planes) >= 2:
            # Intersection of two planes is a line (Cross product of normals)
            v = cross_vectors(planes[0].normal, planes[1].normal)
            if v.length == 0:  # Planes are parallel
                candidate_vector = planes[0].normal
            else:
                candidate_vector = Vector(*v).unitized()
                
        elif len(planes) == 1:
            candidate_vector = planes[0].normal
            
        elif len(vectors) > 0:
            candidate_vector = vectors[0] # Simplification: average or merge half-spaces
            
        # Validate candidate against all half-spaces (Vectors) to ensure no collisions
        if candidate_vector:
            for v in vectors:
                if candidate_vector.dot(v) < 0:
                    # Trying to push through solid wood
                    return None 
                    
        return candidate_vector

    def get_extraction_vector(self, element, active_joints):
        """Gets the final extraction vector for a given element."""
        constraints = [joint.get_kinematic_constraint(element) for joint in active_joints]
        return self.resolve_constraints(constraints)

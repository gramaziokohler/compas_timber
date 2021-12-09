#from compas.datastructures.assembly import Part
from compas.geometry import Frame, Plane, Point, Line, Vector, Box
from compas.geometry import distance_point_point, cross_vectors


class Beam(object):
    """A class to represent timber beams (studs, slats, etc.) with rectangular cross-sections.
    Parameters
    ----------
    frame : :class:`compas.geometry.Frame`.
        A local coordinate system of the beam: 
        Origin is located at the starting point of the centreline.
        x-axis corresponds to the centreline (major axis), usually also the fibre direction in solid wood beams. 
        y-axis corresponds to the width of the cross-section.
        z-axis corresponds to the height of the cross-section.


    width : float.
        Width of the cross-section
    height : float.
        Height of the cross-section
    
    shape : :class:`compas.geometry.Shape`, optional
        The base shape of the part geometry.
    
    Attributes
    ----------

    length : float.
        Length of the beam. 
    
    centreline: :class:``compas.geometry.Line`

    """

    def __init__(self, frame = None, length = None, width = None, height = None):
        self.frame = frame
        self.width = width
        self.height = height
        self.length = length


    def __repr__(self):
        return 'Beam %s x %s x %s at %s'%(self.width,self.height,self.length,self.frame)

    ### constructors ###
    @classmethod
    def from_frame(cls, frame, width=None, height=None, length = None):
        #needed? same as init
        return cls(frame,length,width,height)
    
    @classmethod
    def from_centreline(cls, centreline, z_vector=None, width=None, height=None):
        """
        Define the beam from its centreline. 
        z_vector: a vector indicating the height direction (z-axis) of the cross-section. If not specified, a default will be used.
        """
        x_vector = centreline.vector
        if z_vector==None: z_vector = Vector(0,0,1)  #TODO: default, add other cases
        y_vector = cross_vectors(x_vector, z_vector) * -1.0
        frame = Frame(centreline.p1, x_vector, y_vector)
        length = centreline.length

        return cls(frame,length,width,height)

    @classmethod
    def from_endpoints(cls, point_start, point_end, z_vector=None, width=None, height=None):
        
        x_vector = Vector(point_start, point_end)
        if z_vector==None: z_vector = Vector(0,0,1)  #TODO: default, add other cases
        y_vector = cross_vectors(x_vector, z_vector) * -1.0
        frame = Frame(point_start, x_vector, y_vector)
        length = distance_point_point(point_start, point_end)

        return cls(frame,length,width,height)

    ### main methods and properties ###

    def add_feature(self,feature):
        pass

    @property
    def shape(self):
        """
        Base shape of the beam, i.e. box with no features.
        """
        boxframe = Frame(self.frame.point - self.frame.xaxis*self.width/2 - self.frame.yaxis*self.height/2)
        return Box(boxframe, self.length, self.width, self.height)
    
    @property
    def geometry(self):
        """
        Geometry of the beam with all features (e.g. trims, cuts, notches, holes etc.)
        """
        # apply all self.features to the self.shape through boolean operations(subtractions) ? 

        pass

    ### utils ###

    def move_endpoint(self, which_endpoint='start', vector=Vector(0,0,0)):
        # create & apply a transformation
        pass

    def extend_length(self, d, option='both'):
        """
        options: 'start', 'end', 'both'
        """
        if option in ('start', 'both'): pass #move frame's origin by -d
        if option=='end': pass #change length by d
        if option=='both': pass #chane lenth by 2d 
        return

    def rotate_around_centreline(self, angle, clockwise = False):
        # create & apply a transformation
        pass

    def align_z(self, vector):
        pass



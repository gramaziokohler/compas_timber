class TButtJoint(object):
    def __init__(self, crossbeam, beam_end, gap = 0.00):
        self.crossbeam = crossbeam
        self.beam_end = beam_end
        self.gap = gap #float, additional gap, e.g. for glue


    @property
    def find_side(self):
        """
        calculate which side is the cutting side
        """
        #main beams x-direction outgoing from the connection (this end -> the other end)
        
        
        
        pass
        #return beamside (index)
    

    @property
    def cut_plane(self):
        """
        find side, then get the side's plane, then move it along its z-axis by gap
        """
        pass
        #return plane

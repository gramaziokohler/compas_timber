class PlaneCut(object):
    def __init__(self, part, cutting_frame):

        self.cutting_frame = cutting_frame #need a frame to know which part to discard (z-positive part will be discarded)
        
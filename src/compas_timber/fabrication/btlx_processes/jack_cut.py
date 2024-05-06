class BTLxProcess(object):
    pass


class OrientationType(object):
    START = 0
    END = 1


class JackRafterCut(BTLxProcess):
    def __init__(self, orientation, start_x=0.0, start_y=0.0, start_depth=0.0, angle=90.0, inclination=90.0):
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._inclination = None
        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.inclination = inclination

    @property
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, orientation):
        if orientation not in [OrientationType.START, OrientationType.END]:
            raise ValueError("Orientation must be either OrientationType.START or OrientationType.END.")
        self._orientation = orientation

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, start_x):
        if start_x > 100000.0:
            raise ValueError("Start X must be less than 50000.0.")
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 50000.0:
            raise ValueError("Start Y must be less than 50000.0.")
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 50000.0:
            raise ValueError("Start Depth must be less than 50000.0.")
        self._start_depth = start_depth

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle > 179.9 or angle < 0.1:
            raise ValueError("Angle must be between 0.1 and 179.9.")
        self._angle = angle

    @property
    def inclination(self):
        return self._inclination

    @inclination.setter
    def inclination(self, inclination):
        if inclination > 179.9 or inclination < 0.1:
            raise ValueError("Inclination must be between 0.1 and 179.9.")
        self._inclination = inclination

    @classmethod
    def from_plane_and_beam(cls, plane, beam):
        pass

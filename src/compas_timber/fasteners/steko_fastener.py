from compas.geometry import Transformation

from .anchor import AnchorKind
from .dowel import Dowel
from .fastener import Fastener
from .fastener import FastenerPart


class StekoPlate(FastenerPart):
    pass


class StekoFastener(Fastener):
    ACCEPTS = (AnchorKind.FACE, AnchorKind.AXIS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dowel_diameter = 0.025
        self.dowel_length = 0.4

    def bind(self, anchors: list):
        """
        Bind the fastener to a list of anchors.

        Parameters
        ----------
        anchors : list
            A list of anchors to bind the fastener to.
        """
        anchors = list(anchors)
        wrong = [a for a in anchors if a.kind not in self.ACCEPTS]
        if wrong:
            raise ValueError(f"StekoFastener can only be bound to anchors of kind {self.ACCEPTS}, but got {wrong}")

        for anchor in anchors:
            if anchor.kind == AnchorKind.FACE:
                pass
                # self.parts.append(StekoPlate(anchor))
            elif anchor.kind == AnchorKind.AXIS:
                dowel = Dowel(diameter=self.dowel_diameter, length=self.dowel_length)
                dowel.transform(Transformation.from_frame(anchor.frame))
                self.add_part(dowel)
        return self

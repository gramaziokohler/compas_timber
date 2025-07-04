from .joint import Joint


class GenericJoint(Joint):
    """A GenericJoint is an information-only joint, which does not add any features to the elements it connects.

    It is used to create a first-pass joinery information which can be later used to perform analysis using :class:`~compas_timber.connections.analyzers.BeamGroupAnalyzer`.

    Please use `GenericJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.

    Attributes
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.

    """

    @property
    def __data__(self):
        data_dict = {
            "element_a_guid": self.element_a_guid,
            "element_b_guid": self.element_b_guid,
        }
        data_dict.update(super(GenericJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(**value)
        instance.element_a_guid = value["main_beam_key"]
        instance.element_b_guid = value["cross_beam_key"]
        return instance

    def __init__(self, element_a=None, element_b=None, **kwargs):
        super(GenericJoint, self).__init__(**kwargs)
        self.element_a = element_a
        self.element_b = element_b
        self.element_a_guid = str(element_a.guid) if element_a else None
        self.element_b_guid = str(element_b.guid) if element_b else None

    @property
    def elements(self):
        return [self.element_a, self.element_b]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to elements saved in the model."""
        self.element_a = model.element_by_guid(self.element_a_guid)
        self.element_b = model.element_by_guid(self.element_b_guid)

    def add_features(self):
        """This joint does not add any features."""
        pass

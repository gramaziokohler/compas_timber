from .dovetail_mortise import DovetailMortise
from .dovetail_tenon import DovetailTenon
from .mortise import Mortise
from .tenon import Tenon


class _NestedProcessing(object):
    """Carries the single nested processing of a :class:`House` or a :class:`HouseMortise`, which the schema allows in addition to the parameters of the base class."""

    NESTED_TYPES = ()

    def __init__(self, *args, subprocessings=None, **kwargs):
        super(_NestedProcessing, self).__init__(*args, **kwargs)
        for subprocessing in subprocessings or []:
            self.add_subprocessing(subprocessing)

    @property
    def __data__(self):
        data = super(_NestedProcessing, self).__data__
        data["subprocessings"] = self.subprocessings
        return data

    def add_subprocessing(self, subprocessing):
        """Add the nested processing.

        Parameters
        ----------
        subprocessing : :class:`~compas_timber.fabrication.BTLxProcessing`
            The nested processing. Its parameters refer to the element, not to this processing.

        Raises
        ------
        ValueError
            If the type of the processing cannot be nested here, or if there already is a nested processing.

        """
        if type(subprocessing) not in self.NESTED_TYPES:
            raise ValueError("A {} can only hold one of {}. Got: {}".format(self.PROCESSING_NAME, self.NESTED_TYPES, type(subprocessing)))
        if self.subprocessings:
            raise ValueError("A {} can only hold a single nested processing.".format(self.PROCESSING_NAME))
        super(_NestedProcessing, self).add_subprocessing(subprocessing)

    def scale(self, factor):
        """Scale the parameters of this processing and of the nested one by a given factor.

        Parameters
        ----------
        factor : float
            The scaling factor.

        """
        super(_NestedProcessing, self).scale(factor)
        for subprocessing in self.subprocessings or []:
            subprocessing.scale(factor)


class House(_NestedProcessing, Tenon):
    """Represents a House feature: a shallow, wide tenon on which a nested tenon can sit.

    Has the same parameters as a :class:`~compas_timber.fabrication.Tenon`, and optionally a nested :class:`~compas_timber.fabrication.Tenon` or
    :class:`~compas_timber.fabrication.DovetailTenon` whose parameters refer to the element. Its `start_x` and `start_depth` place it on the end face of the house.

    Parameters
    ----------
    subprocessings : list(:class:`~compas_timber.fabrication.BTLxProcessing`), optional
        The nested processing.

    """

    PROCESSING_NAME = "House"  # type: ignore
    NESTED_TYPES = (Tenon, DovetailTenon)

    def apply(self, geometry, beam):
        """Apply the house, and the nested processing if there is one, to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas_brep.Brep`
            The geometry to be processed.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is milled by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If any of the two cannot be applied.

        Returns
        -------
        :class:`~compas_brep.Brep`
            The resulting geometry after processing.

        """
        geometry = super(House, self).apply(geometry, beam)
        for subprocessing in self.subprocessings or []:
            geometry = subprocessing.apply(geometry, beam)
        return geometry


class HouseMortise(_NestedProcessing, Mortise):
    """Represents a HouseMortise feature: a shallow, wide mortise from whose bottom a nested mortise can continue.

    Has the same parameters as a :class:`~compas_timber.fabrication.Mortise`, and optionally a nested :class:`~compas_timber.fabrication.Mortise` or
    :class:`~compas_timber.fabrication.DovetailMortise` whose parameters refer to the element. Its `start_depth` places it on the bottom of the house.

    Parameters
    ----------
    subprocessings : list(:class:`~compas_timber.fabrication.BTLxProcessing`), optional
        The nested processing.

    """

    PROCESSING_NAME = "HouseMortise"  # type: ignore
    NESTED_TYPES = (Mortise, DovetailMortise)

    def apply(self, geometry, beam):
        """Apply the house mortise, and the nested processing if there is one, to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas_brep.Brep`
            The geometry to be processed.
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is milled by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If any of the two cannot be applied.

        Returns
        -------
        :class:`~compas_brep.Brep`
            The resulting geometry after processing.

        """
        geometry = super(HouseMortise, self).apply(geometry, beam)
        for subprocessing in self.subprocessings or []:
            if type(subprocessing) is Mortise:
                # Mortise ignores its start_depth, so it digs from the reference side instead. That stays inside of the house, down to the bottom of the nested mortise.
                subprocessing = subprocessing.copy()
                subprocessing.depth += subprocessing.start_depth
            geometry = subprocessing.apply(geometry, beam)
        return geometry

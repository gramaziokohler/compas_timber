from struct import pack
from compas_timber.utils.workflow import FeatureDefinition

if Beam and Pln:
    Ft = [FeatureDefinition('trim', p, b) for b in Beam for p in Pln]

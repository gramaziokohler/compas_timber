from warnings import warn

from compas.data import Data

import compas_timber


class DataVersionMixin(Data):
    """
    This mixin adds versioning information to the data representation of a class,
    allowing for compatibility checks when loading data created with different versions of the library.
    """

    @property
    def __data__(self):
        data = super().__data__
        data["__version__"] = compas_timber.__version__
        return data

    @classmethod
    def __from_data__(cls, data):
        version = data.pop("__version__", None)
        if version is not None:
            if version != compas_timber.__version__:
                warn(
                    f"Data was created with compas_timber version {version}, but you are using version {compas_timber.__version__}. "
                    "This may lead to incompatibilities and errors. Consider updating the data or using an older version of compas_timber."
                )
        return super().__from_data__(data)

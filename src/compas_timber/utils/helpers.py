__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska"]
__license__ = "MIT"
__version__ = "20.09.2022"

from math import fabs


def close(x, y, tol=1e-12):
    """
    Shorthand for comparing two numbers or None.
    """
    if x == None and y == None:
        return True
    return fabs(x - y) < tol  # same as close() in compas.geometry


def are_objects_identical(object1, object2, attributes_to_compare):
    """
    Generic method to check if objects are practically identical
    """

    if type(object1) != type(object2):
        return False

    def _get_val(obj, attr_name):

        # if attr_name in obj.__dir__:
        attrobj = getattr(
            obj.__class__, attr_name
        )  # TODO: does not find defined attributes, only properties - why?
        if isinstance(attrobj, property):
            val = attrobj.__get__(obj, obj.__class__)
            return val
        else:
            NotImplementedError

    for attr_name in attributes_to_compare:
        val1 = getattr(object1, attr_name)
        val2 = getattr(object2, attr_name)
        if val1 != val2:
            return False

    return True


# @array_function_dispatch(_isclose_dispatcher)
# def isclose(a, b, rtol=1.e-5, atol=1.e-8, equal_nan=False):
#     #source https://github.com/numpy/numpy/blob/v1.22.4/numpy/core/numeric.py#L2259-L2381
#     """
#     Returns a boolean array where two arrays are element-wise equal within a
#     tolerance.
#     The tolerance values are positive, typically very small numbers.  The
#     relative difference (`rtol` * abs(`b`)) and the absolute difference
#     `atol` are added together to compare against the absolute difference
#     between `a` and `b`.
#     .. warning:: The default `atol` is not appropriate for comparing numbers
#                  that are much smaller than one (see Notes).
#     Parameters
#     ----------
#     a, b : array_like
#         Input arrays to compare.
#     rtol : float
#         The relative tolerance parameter (see Notes).
#     atol : float
#         The absolute tolerance parameter (see Notes).
#     equal_nan : bool
#         Whether to compare NaN's as equal.  If True, NaN's in `a` will be
#         considered equal to NaN's in `b` in the output array.
#     Returns
#     -------
#     y : array_like
#         Returns a boolean array of where `a` and `b` are equal within the
#         given tolerance. If both `a` and `b` are scalars, returns a single
#         boolean value.
#     See Also
#     --------
#     allclose
#     math.isclose
#     Notes
#     -----
#     .. versionadded:: 1.7.0
#     For finite values, isclose uses the following equation to test whether
#     two floating point values are equivalent.
#      absolute(`a` - `b`) <= (`atol` + `rtol` * absolute(`b`))
#     Unlike the built-in `math.isclose`, the above equation is not symmetric
#     in `a` and `b` -- it assumes `b` is the reference value -- so that
#     `isclose(a, b)` might be different from `isclose(b, a)`. Furthermore,
#     the default value of atol is not zero, and is used to determine what
#     small values should be considered close to zero. The default value is
#     appropriate for expected values of order unity: if the expected values
#     are significantly smaller than one, it can result in false positives.
#     `atol` should be carefully selected for the use case at hand. A zero value
#     for `atol` will result in `False` if either `a` or `b` is zero.
#     `isclose` is not defined for non-numeric data types.
#     `bool` is considered a numeric data-type for this purpose.
#     Examples
#     --------
#     >>> np.isclose([1e10,1e-7], [1.00001e10,1e-8])
#     array([ True, False])
#     >>> np.isclose([1e10,1e-8], [1.00001e10,1e-9])
#     array([ True, True])
#     >>> np.isclose([1e10,1e-8], [1.0001e10,1e-9])
#     array([False,  True])
#     >>> np.isclose([1.0, np.nan], [1.0, np.nan])
#     array([ True, False])
#     >>> np.isclose([1.0, np.nan], [1.0, np.nan], equal_nan=True)
#     array([ True, True])
#     >>> np.isclose([1e-8, 1e-7], [0.0, 0.0])
#     array([ True, False])
#     >>> np.isclose([1e-100, 1e-7], [0.0, 0.0], atol=0.0)
#     array([False, False])
#     >>> np.isclose([1e-10, 1e-10], [1e-20, 0.0])
#     array([ True,  True])
#     >>> np.isclose([1e-10, 1e-10], [1e-20, 0.999999e-10], atol=0.0)
#     array([False,  True])
#     """
#     def within_tol(x, y, atol, rtol):
#         with errstate(invalid='ignore'):
#             return less_equal(abs(x-y), atol + rtol * abs(y))

#     x = asanyarray(a)
#     y = asanyarray(b)

#     # Make sure y is an inexact type to avoid bad behavior on abs(MIN_INT).
#     # This will cause casting of x later. Also, make sure to allow subclasses
#     # (e.g., for numpy.ma).
#     # NOTE: We explicitly allow timedelta, which used to work. This could
#     #       possibly be deprecated. See also gh-18286.
#     #       timedelta works if `atol` is an integer or also a timedelta.
#     #       Although, the default tolerances are unlikely to be useful
#     if y.dtype.kind != "m":
#         dt = multiarray.result_type(y, 1.)
#         y = asanyarray(y, dtype=dt)

#     xfin = isfinite(x)
#     yfin = isfinite(y)
#     if all(xfin) and all(yfin):
#         return within_tol(x, y, atol, rtol)
#     else:
#         finite = xfin & yfin
#         cond = zeros_like(finite, subok=True)
#         # Because we're using boolean indexing, x & y must be the same shape.
#         # Ideally, we'd just do x, y = broadcast_arrays(x, y). It's in
#         # lib.stride_tricks, though, so we can't import it here.
#         x = x * ones_like(cond)
#         y = y * ones_like(cond)
#         # Avoid subtraction with infinite/nan values...
#         cond[finite] = within_tol(x[finite], y[finite], atol, rtol)
#         # Check for equality of infinite values...
#         cond[~finite] = (x[~finite] == y[~finite])
#         if equal_nan:
#             # Make NaN == NaN
#             both_nan = isnan(x) & isnan(y)

#             # Needed to treat masked arrays correctly. = True would not work.
#             cond[both_nan] = both_nan[both_nan]

#         return cond[()]  # Flatten 0d arrays to scalars

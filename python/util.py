import numpy as np
from scipy.ndimage import correlate1d

def memoize(function):
    """Provides a decorator for memoizing functions"""
    from functools import wraps
    memo = {}

    @wraps(function)
    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv
    return wrapper

@memoize
def _gaussian_weights(sigma):
    """Gaussian kernel exactly as scipy.ndimage.gaussian_filter1d builds it (truncate=4)"""
    radius = int(4.0 * sigma + 0.5)
    x = np.arange(-radius, radius + 1)
    weights = np.exp(-0.5 / (sigma * sigma) * x ** 2)
    return (weights / weights.sum())[::-1]


def blur(array, sigma):
    """gaussian_filter1d along the last axis, with the kernel built once per sigma

    Effects blur every frame with the same few sigmas, and building the kernel
    each call cost more than the blur itself. Blurs each row of a 2D array.
    """
    if sigma <= 0:
        return array
    return correlate1d(array, _gaussian_weights(float(sigma)), axis=-1, mode="reflect")


@memoize
def _normalized_linspace(size):
    return np.linspace(0, 1, size)

def interpolate(y, new_length):
    """Intelligently resizes the array by linearly interpolating the values

    Parameters
    ----------
    y : np.array
        Array that should be resized

    new_length : int
        The length of the new interpolated array

    Returns
    -------
    z : np.array
        New array with length of new_length that contains the interpolated
        values of y.
    """
    if len(y) == new_length:
        return y
    x_old = _normalized_linspace(len(y))
    x_new = _normalized_linspace(new_length)
    z = np.interp(x_new, x_old, y)
    return z


def interpolate_rows(array, new_length):
    """interpolate() applied to each row of a 2D array"""
    return np.array([interpolate(row, new_length) for row in array])

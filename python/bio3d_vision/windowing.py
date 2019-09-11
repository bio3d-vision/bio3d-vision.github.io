"""Load and prepare datasets saved on disk. This includes preprocessing and
windowing.

"""
import math

import numpy as np

from typing import List, Sequence, Generator


# Random States
corner_generation_random_state = np.random.RandomState()


def window_generator(data_volume: np.ndarray,
                     window_shape: Sequence[int],
                     corner_points: List[List[int]]) -> \
        Generator[np.ndarray, int, None]:
    """

    Args:
        data_volume (np.ndarray): The volume to be preprocessed.
        window_shape (Sequence[int]): The 2D or 3D size of the windows to
            be output. (x, y) for 2D and (z, x, y) for 3D.
        corner_points (List[List[int], List[int], List[int]]): A list
            specifying the upper-leftmost corner of the windows.

    Returns: Generator of windows.
    """
    # Note whether the window is 2D or 3D for later
    window_is_3d = len(window_shape) == 3
    # Make 2D stuff 3D
    if len(window_shape) == 2:
        window_shape = [1] + list(window_shape)

    # Shape of the volumes, and number of dimensions
    # Currently assumes that data will be 2D single channel (2d shape),
    # 3D single channel (3d shape)

    # Is the spatial shape 3D?
    vol_is_3d = data_volume.ndim > 2

    if data_volume.ndim == 2:
        # Add a singleton z spatial dimension
        data_volume = np.expand_dims(data_volume, 0)

    # Volumes' spatial shape
    spatial_shape = data_volume.shape[:]

    # Create windows

    # Calculate the number of windows
    n_windows = 1
    for p in corner_points:
        n_windows *= len(p)

    # Shape of each batch source array. Add in the channel axis:
    # Note the format is either NCXY or NCZXY
    array_shape = [n_windows] + list(window_shape)
    # Remove the z axis if the window is not 3D
    if not window_is_3d or not vol_is_3d:
        array_shape.pop(1)

    # For convenience
    dz = window_shape[0]
    dx = window_shape[1]
    dy = window_shape[2]
    zs = spatial_shape[0]
    xs = spatial_shape[1]
    ys = spatial_shape[2]

    def get_range(n0: int, n1: int, ns: int) -> List[int]:
        """Get a window range along axis n, accounting for reflecting
        boundary conditions when the range is out-of-bounds within the
        source volume.

        Args:
            n0 (int): Window starting point.
            n1 (int): Window ending point.
            ns (int): Source volume size along axis n.

        Returns:
            (List[int]): Window range.

        """

        # Return a range as a list
        def lrange(a, b, n=1) -> List[int]:
            return list(range(a, b, n))

        # Get the in-bounds part of the range
        n_range = lrange(max(0, n0), min(ns, n1))
        # Handle out-of-bounds indices by reflection across boundaries
        if n0 < 0:
            # Underflow
            n_range = lrange(-n0, 0, -1) + n_range
        if n1 > ns:
            # Overflow
            n_range = n_range + lrange(ns - 1, 2 * ns - n1 - 1, -1)

        return n_range

    # Add windows to the batch source arrays
    window_idx = 0
    # Window augmentation parameters
    for z in corner_points[0]:
        for x in corner_points[1]:
            for y in corner_points[2]:

                # Use window_shape-sized windows
                z0 = z
                z1 = z0 + dz
                x0 = x
                x1 = x0 + dx
                y0 = y
                y1 = y0 + dy

                # Compute window ranges
                z_range = get_range(z0, z1, zs)
                x_range = get_range(x0, x1, xs)
                y_range = get_range(y0, y1, ys)

                # Get window extent from the calculated ranges
                window = data_volume.take(z_range, axis=0) \
                    .take(x_range, axis=1) \
                    .take(y_range, axis=2)
                if not window_is_3d or not vol_is_3d:
                    # Remove singleton z dimension for 2D windows
                    window = np.squeeze(window, axis=0)

                window_idx += 1
                yield window

    return None


def gen_conjugate_corners(corner_points: List[List[int]],
                          window_shape: List[int],
                          conjugate_window_shape: List[int]) -> \
        List[List[int]]:
    """
    Given a list of corner points generated using `gen_corner_points()`
    with the window_shape parameter, shift the corner points to obtain larger
    windows of size conjugate_window_shape such that both corner points
    generate windows centered at the same location. For example, given
    corner point [10, 20, 18] generated using window size [2, 4, 3], and given
    conjugate_window_shape [4, 8, 5] the conjugate corner point is [9, 18, 17].

    Args:
        corner_points (List[List[int]]): List of upper left-most corners of
            windows of size `window_shape``.
        window_shape (List[int]): 2D or 3D size of windows corresponding to
            `corner_points`.
        conjugate_window_shape (List[int]): Desired window size of windows
            centered at the same locatin as those with given `corner_points`.
            Size in each dimension must be larger than `window_shape`.
    Returns: List[List[int]] The new list of corner points.

    """
    conjugate_window_shape = np.array(conjugate_window_shape)
    window_shape = np.array(window_shape)

    # Window shapes must have the same number of dimensions
    assert len(conjugate_window_shape) == len(window_shape)
    # In order for windows to have the same center their difference must be
    # divisible by 2
    assert sum((conjugate_window_shape-window_shape) % 2) == 0
    # Compute difference in shape
    d_shape = [int((i - o) / 2) for i, o in zip(conjugate_window_shape,
                                                window_shape)]

    # Generate corners.
    conjugate_corners = []
    for i in range(len(corner_points)):
        corner_points_k = []
        for k in corner_points[i]:
            corner_points_k.append(k-d_shape[i])
        conjugate_corners.append(corner_points_k)
    return conjugate_corners


def gen_corner_points(spatial_shape: Sequence[int],
                      window_shape: Sequence[int],
                      window_spacing: Sequence[int],
                      random_windowing: bool = True,
                      random_seed: int = None) -> List[List[int]]:
    """Generate lists of Z, X, and Y coordinates for the window
    corner points. If random windowing is set to True, the corner generation
    is randomized.

    Args:
        spatial_shape (Sequence[int]): Spatial_shape of volume.
        window_shape (Sequence[int]): Spatial shape of windows. Must consist of
            3 integers. Use [1, X, Y] for 2D windows.
        window_spacing (Sequence[int]): Spacing between the corners of
            consecutive windows along each spatial axis in training mode.
            Should be in (dx, dy) format for 2D windows and
            (dz, dx, dy) format for 3D windows. Example: If
            `window_spacing=[1, 80, 80]`, the first window corner
            will be at [0, 0, 0], and the second will be at [0, 0, 80].
        random_windowing (bool): If True, the window generation is randomized.
            Uses random_seed.
        random_seed (int): Seed to control the Numpy random number
            generator. Only used if random_windowing is True.
    Returns:
        (List[List[int], List[int], List[int]]): Corner point Z, X,
            and Y coordinate lists, respectively.

    """

    # Set the random seed
    if random_seed is None:
        # Create a new seed
        random_seed = np.random.randint(np.iinfo(np.int32).max)

    corner_generation_random_state.seed(random_seed)

    corners = []

    # Number of spatial dimensions
    nsdim = len(spatial_shape)

    for k in range(nsdim):
        vs = spatial_shape[k]
        w = window_shape[k]
        d = window_spacing[k]

        usable_length = vs - w + 1

        if usable_length == 1:
            # Singleton dimension along axis k
            corners_k = [0]
        else:
            n_bins = int(math.ceil(usable_length / d))

            if random_windowing:
                bins = [min(d * i, usable_length)
                for i in range(n_bins + 1)]

                # Output window corner point coordinates along axis k
                corners_k = \
                    [corner_generation_random_state.randint(bins[i], bins[i + 1])
                     for i in range(n_bins)]

            else:
                # Output window corner point coordinates along axis k
                corners_k = [d * i for i in range(n_bins)]
                # Additional one to make sure we get full coverage
                if corners_k[-1] != usable_length - 1:
                    corners_k.append(usable_length - 1)

        corners.append(corners_k)

    return corners

"""Load and prepare datasets saved on disk. This includes preprocessing and
windowing.

"""
import logging
import math
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import tifffile as tif

from scipy.ndimage.interpolation import zoom, map_coordinates
from scipy.ndimage.filters import gaussian_filter

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, \
    TypeVar, Union, Generator

# DataRanges specify which portion of a 3D volume to use for training or
# validation. Each DataRange is either a tuple of 2 slice objects for x and y
# ranges, or a tuple of 3 slice objects for z, x, and y ranges.
DataRange = TypeVar(Union[Tuple[slice, slice], Tuple[slice, slice, slice]])
# A source for a data volume can either be a string, indicating a path to a
# file saved to disk, or it can be a NumPy array.
VolSource = TypeVar(Union[str, np.ndarray])

# Random States
window_generation_random_state = np.random.RandomState()
deformation_random_state = np.random.RandomState()


def window_generator(data_volume: np.ndarray,
                     window_shape: Optional[Sequence[int]] = None,
                     window_spacing: Optional[Sequence[int]] = None,
                     forward_window_overlap: Optional[Sequence[int]] = None,
                     random_windowing: bool = False,
                     random_seed: int = None) -> \
        Generator[np.ndarray, int, None]:
    """

    Args:
        data_volume (np.ndarray): The volume to be preprocessed.
        window_shape (Sequence[int]): The 2D or 3D size of the windows to
            be output. (x, y) for 2D and (z, x, y) for 3D.
        window_spacing (Sequence[int]): Spacing between the corners of
            consecutive windows along each spatial axis in training mode.
            Should be in (dx, dy) format for 2D windows and
            (dz, dx, dy) format for 3D windows. Example: If
            `window_spacing=[1, 80, 80]`, the first window corner
            will be at [0, 0, 0], and the second will be at [0, 0, 80].
            If window_spacing is set it overrides the forward window_overlap.
        forward_window_overlap (Sequence[int]): Overlap between
            successive windows during forward (inference) passes through
            a network. Used to mitigate edge effects caused by
            partitioning a large volume into independent windows for
            segmentation. Default is no overlap. Only used if window_spacing
            is set to None.
        random_windowing (bool): If True, the window generation is randomized.
            Uses random_seed.
        random_seed (int): Seed to control the Numpy random number
            generator. Only used if random_windowing is True.

    Returns: #TODO
    """
    if forward_window_overlap is None:
        forward_window_overlap = [0, 0, 0]
    # Note whether the window is 2D or 3D for later
    window_is_3d = len(window_shape) == 3
    # Make 2D stuff 3D
    if len(window_shape) == 2:
        window_shape = [1] + list(window_shape)
    if window_spacing is not None and len(window_spacing) == 2:
        window_spacing = [1] + list(window_spacing)
    if window_spacing is None:
        window_spacing = [s - o for s, o in zip(window_shape,
                                                forward_window_overlap)]
    # Set the random seed
    if random_seed is None:
        # Create a new seed
        random_seed = np.random.randint(np.iinfo(np.int32).max)

    window_generation_random_state.seed(random_seed)

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
    # Number of spatial dimensions
    nsdim = len(spatial_shape)

    # Generate window corner points
    corner_points = _gen_corner_points(spatial_shape,
                                       window_shape,
                                       window_spacing)

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


def load(data_dir: Optional[str] = os.path.join('platelet-em', 'images'),
         data_file: Optional[Union[str, np.ndarray]] = '50-images.tif',
         data_range: Optional[DataRange] = None,
         data_type: Union[np.float32, np.int32] = np.float32):
    """Load data from the file system.

    Args:
        data_vol_dir (str): String specifying the location of the source
            data.
        data_file (Optional[VolSource]): Name of the data image
            volume within the data_dir, or a numpy array.
        data_range (Optional[DataRange]): Range of the loaded
            volume to use, represented as a tuple of 2 or 3 slice objects.
        data_type (Union[np.float32, np.int32]): Cast the data to this type.

    Returns: (np.ndarray) The data volume loaded.

    """
    # Prepare the training volume range slicing
    if data_range is None:
        train_range = (slice(None), slice(None), slice(None))
    elif len(data_range) == 2:
        data_range = (slice(None), data_range[0], data_range[1])

    # Load volume
    if isinstance(data_dir, str) and isinstance(data_file, str):
        data_volume = \
            tif.imread(os.path.join(data_dir,
                                    data_file)).astype(data_type)
    elif isinstance(data_file, np.ndarray):
        data_volume = data_file.astype(data_type)
    else:
        raise ValueError(f'Need to either specify strings for both data_dir' \
                         f'and data_file or supply data_file as np.ndarray. ')

    # Make a 2D volume 3D
    if data_volume.ndim == 2:
        data_volume = np.expand_dims(data_volume, axis=0)
    # Slice
    data_volume = data_volume[data_range]

    return data_volume


def deform(volumes: Union[np.ndarray, Sequence[np.ndarray]],
           deformation_settings: Optional[Dict[str, Any]] = None,
           random_seed: int = None) -> \
        List[np.ndarray]:
    """Apply an elastic deformation to a collection of image volumes.

    Args:
        volumes (Union[np.ndarray, Sequence[np.ndarray]]): One or more
            numpy arrays to deform.
        deformation_settings (Optional[Dict[str, Any]]): Elastic deformation
            settings. By default elastic deformation is turned off.
        random_seed (int): Seed to control the Numpy random number
            generator.

    Returns:
        (List[np.ndarray]): List of deformed volumes.

    """
    # Set the random seed
    if random_seed is None:
        # Create a new seed
        random_seed = np.random.randint(np.iinfo(np.int32).max)

    deformation_random_state.seed(random_seed)

    # Image deformation default settings
    if deformation_settings is None:
        deformation_settings = {}
    if 'scale' not in deformation_settings:
        deformation_settings['scale'] = 40
    if 'alpha' not in deformation_settings:
        deformation_settings['alpha'] = 20
    if 'sigma' not in deformation_settings:
        deformation_settings['sigma'] = 0.6

    # Make sure xy shape (last two axes) are the same for all volumes
    xy_shapes = [v.shape[-2:] for v in volumes]
    if xy_shapes.count(xy_shapes[0]) != len(xy_shapes):
        # True when xy shapes don't all match
        raise ValueError('Volumes passed to deform() must '
                         'all have the same shape.')

    # Build a new pixel index deformation map
    # Assumed to be the same
    xy_shape = xy_shapes[0]
    deform_map = _deformation_map(xy_shape, deformation_settings)

    deformed_volumes = []

    for volume in volumes:
        shape = volume.shape
        ndim = volume.ndim
        new_vol = np.zeros_like(volume)
        if ndim == 4:
            # 3D multichannel data. Apply 2D deformations to each z slice
            # in each channel of the volume
            for c in range(shape[0]):
                for z in range(shape[1]):
                    new_vol[c, z, ...] = \
                        map_coordinates(volume[c, z, ...],
                                        deform_map,
                                        order=0).reshape(xy_shape)
        elif ndim == 3:
            # 3D single channel data. Apply 2D deformations to each z slice
            # of the volume
            for z in range(shape[0]):
                new_vol[z, ...] = map_coordinates(volume[z, ...],
                                                  deform_map,
                                                  order=0).reshape(xy_shape)
        elif ndim == 2:
            # Volume is 2D, deform the whole thing at once
            new_vol = map_coordinates(volume,
                                      deform_map,
                                      order=0).reshape(xy_shape)
        else:
            raise ValueError(f'Cannot deform volume with ndim {ndim}')

        deformed_volumes.append(new_vol)
        if isinstance(volumes, np.ndarray):
            return deformed_volumes[0]
        else:
            return deformed_volumes


def _deformation_map(shape: Sequence[int],
                     deformation_settings: Dict[str, Any]) -> \
        Tuple[np.ndarray, np.ndarray]:
    """Create an elastic deformation map,

    Deformation map may be applied to, e.g., image, label,
    and error weight data.
    Adapted from:
    https://gist.github.com/chsasank/4d8f68caf01f041a6453e67fb30f8f5a
    (October 30, 2016).

    Args:
        shape (Sequence[int]): Shape of the dataset the deformation map
            will be applied to. Should be 2D (for now).

    Return:
        (Tuple[np.ndarray, np.ndarray]): A deformation map, represented as
            a pair of lists of x and y indices.

    """
    if len(shape) != 2:
        raise TypeError(f'Input shape should be length 2, but is {shape}')

    # Controls the spatial scale of the distortions. A large value
    # creates larger-scale distortions. The image's spatial shape should
    # be evenly divisible by the scale value # TODO: Fix this
    scale = deformation_settings['scale']
    # Distortion average magnitude
    alpha = deformation_settings['alpha']
    # Distortion magnitude standard deviation
    sigma = deformation_settings['sigma']

    # Sample Gaussian distribution on a more coarse grid, then upsample
    # and interpolate
    shape_small = [int(s / float(scale)) for s in shape]

    # Calculate x index translations
    dx_small \
        = gaussian_filter((deformation_random_state.rand(*shape_small) * 2 - 1),
                          sigma,
                          mode='reflect') * alpha
    # Calculate y index translations
    dy_small \
        = gaussian_filter((deformation_random_state.rand(*shape_small) * 2 - 1),
                          sigma,
                          mode='reflect') * alpha

    # Calculate zoom scale
    scale_up = [i / float(j) for i, j in zip(shape, shape_small)]

    # Upsample and interpolate for smooth index translations
    dx = zoom(dx_small, scale_up)
    dy = zoom(dy_small, scale_up)

    x, y = np.meshgrid(np.arange(shape[0]), np.arange(shape[1]),
                       indexing='ij')
    indices = np.reshape(np.clip(x + dx, 0, shape[0] - 1), (-1, 1)), \
              np.reshape(np.clip(y + dy, 0, shape[1] - 1), (-1, 1))

    return indices


def _gen_corner_points(spatial_shape: Sequence[int],
                       window_shape: Sequence[int],
                       window_spacing: Sequence[int],
                       random_windowing: bool = False) -> List[List[int]]:
    """Generate lists of Z, X, and Y coordinates for the window
    corner points. If random windowing is on the corner generation is
    randomized.

    Returns:
        (List[List[int], List[int], List[int]]): Corner point Z, X,
            and Y coordinate lists, respectively.

    """
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
                    [window_generation.random_state.randint(bins[i], bins[i + 1])
                     for i in range(n_bins)]

            else:
                # Output window corner point coordinates along axis k
                corners_k = [d * i for i in range(n_bins)]
                # Additional one to make sure we get full coverage
                if corners_k[-1] != usable_length - 1:
                    corners_k.append(usable_length - 1)

        corners.append(corners_k)

    return corners


def imshow(x, figsize, *args, frame=True, **kwargs):
    f, ax = plt.subplots(1, figsize=figsize)
    f.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.imshow(x, *args, extent=(0, 1, 1, 0), **kwargs)
    ax.axis('tight')
    if frame:
        ax.get_xaxis().set_ticks([])
        ax.get_yaxis().set_ticks([])
    else:
        ax.axis('off')
    pass


if __name__ == "__main__":
    main_data_dir = sys.argv[1]
    window_generation_random_seed = int(sys.argv[2])
    deformation_random_seed = int(sys.argv[3])
    # main_data_dir = os.path.join('platelet-em')
    # main_data_dir = '/home/matt/Desktop/platelet-lcimb'
    train_data_dir = os.path.join(main_data_dir, 'images')
    train_data_file = '50-images.tif'
    train_data_volume = load(train_data_dir, train_data_file)
    imshow(train_data_volume[0][0], (4, 4))
    # User would want to add some logic to normalize the data here
    train_data_volume = deform(train_data_volume,
                               random_seed=deformation_random_seed)
    imshow(train_data_volume[0], (4, 4))
    # train_data_generator = window_generator(train_data_volume)
    window_generator = window_generator(
        train_data_volume,
        window_shape=[3, 200, 200],
        random_windowing=True,
        random_seed=window_generation_random_seed)

    for i, w in enumerate(window_generator):
        if i == 10:
            imshow(w[0], (4, 4))
            tif.imsave(f"test{window_generation_random_seed}_{deformation_random_seed}.tif", w)

    plt.show()

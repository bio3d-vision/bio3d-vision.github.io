"""Functions for doing data augmentation on 2D and 3D image regions.

"""
import numpy as np

from scipy.ndimage.interpolation import zoom, map_coordinates
from scipy.ndimage.filters import gaussian_filter

from typing import Any, Dict, Optional, Sequence, Tuple

def deform(volume: np.ndarray,
           deformation_settings: Optional[Dict[str, Any]] = None,
           random_seed: int = None) -> \
        np.ndarray:
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

    # Build a new pixel index deformation map
    # Assumed to be the same
    xy_shape = volume.shape[-2:]
    deform_map = _deformation_map(xy_shape, deformation_settings)

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

    return new_vol


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
"""Function for loading bio3d-vision dataset files on disk into numpy.

"""
import os

import numpy as np
import tifffile as tif

from typing import Optional, Union

# A source for a data volume can either be a string, indicating a path to a
# file saved to disk, or it can be a NumPy array.
VolSource = Union[str, np.ndarray]


def load(data_dir: Optional[str] = os.path.join('platelet-em', 'images'),
         data_file: Optional[Union[str, np.ndarray]] = '50-images.tif',
         data_type: Union[np.float32, np.int32] = np.float32):
    """Load data from the file system.

    Args:
        data_dir (str): String specifying the location of the source
            data.
        data_file (Optional[VolSource]): Name of the data image
            volume within the data_dir, or a numpy array.
        data_range (Optional[DataRange]): Range of the loaded
            volume to use, represented as a tuple of 2 or 3 slice objects.
        data_type (Union[np.float32, np.int32]): Cast the data to this type.

    Returns: (np.ndarray) The data volume loaded.

    """
    # Load volume
    if isinstance(data_dir, str) and isinstance(data_file, str):
        data_volume = \
            tif.imread(os.path.join(data_dir,
                                    data_file)).astype(data_type)
    elif isinstance(data_file, np.ndarray):
        data_volume = data_file.astype(data_type)
    else:
        raise ValueError(f'Need to either specify strings for both data_dir'
                         f'and data_file or supply data_file as np.ndarray. ')

    # Make a 2D volume 3D
    if data_volume.ndim == 2:
        data_volume = np.expand_dims(data_volume, axis=0)

    return np.squeeze(data_volume)

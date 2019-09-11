import os

import numpy as np
import tifffile as tif

from typing import Optional, Dict, Tuple

platelet_em_rgb_map = {
    (0, 0, 0): 0,
    (1, 1, 224): 1,
    (1, 171, 254): 2,
    (1, 254, 1): 3,
    (255, 224, 0): 4,
    (250, 94, 0): 5,
    (245, 0, 203): 6}

platelet_em_index_to_class = {
    0: 'background',
    1: 'cell',
    2: 'mitochondrion',
    3: 'alpha granule',
    4: 'canalicular vessel',
    5: 'dense granule',
    6: 'dense granule core'}


def convert_platelet_files(dataset_dir: str) -> None:
    """

    Args:
        dataset_dir (str):

    Returns: None

    """
    semantic_dir = os.path.join(dataset_dir, 'labels-semantic')
    semantic_tifs = [os.path.join(semantic_dir, f)
                     for f in os.listdir(semantic_dir)
                     if '.tif' in os.path.splitext(f)[1].lower()]
    for f in semantic_tifs:
        rgb = tif.imread(f)
        index = rgb_to_index(rgb, semantic_index_map('platelet-em'))
        tif.imsave(f, index)
        print(f'Converted {f}.')

    instance_dir = os.path.join(dataset_dir, 'labels-instance')
    instance_tifs = [os.path.join(instance_dir, f)
                     for f in os.listdir(instance_dir)
                     if '.tif' in os.path.splitext(f)[1].lower()]

    for f in instance_tifs:
        rgb = tif.imread(f)
        index = rgb_to_index(rgb)
        tif.imsave(f, index)
        print(f'Converted {f}.')

    pass


def semantic_index_map(dataset_name: str) -> Dict[Tuple[int, int, int], int]:
    """Return the semantic index mapping for a named dataset in the
    bio3d-vision collection.

    Semantic index mappings indicates which colors in the dataset's semantic
    label files correspond to which semantic class indices.

    Args:
        dataset_name (str):

    Returns:
        (Dict[Tuple[int, int, int], int])

    """
    if dataset_name == 'platelet-em':
        return platelet_em_rgb_map

    else:
        raise ValueError(f"Dataset name {dataset_name} not recognized. "
                         f"Possible choices are: 'platelet-em'.")


def rgb_to_index(
        rgb: np.ndarray,
        color_map: Optional[Dict[Tuple[int, int, int], int]] = None) -> \
        np.ndarray:
    """

    Args:
        rgb:
        color_map:

    Returns:

    """
    if color_map is not None:
        def f_rgb(color: np.ndarray):
            cr, cg, cb = color.astype(np.int)
            return color_map[(cr, cg, cb)]

    else:
        # Make sure black is always index 0
        unique_colors = [(0, 0, 0)]

        def f_rgb(color: np.ndarray):
            tcolor = tuple(color)
            if tcolor not in unique_colors:
                unique_colors.append(tcolor)
            return unique_colors.index(tcolor)

    return np.apply_along_axis(f_rgb, -1, rgb).astype(np.uint16)

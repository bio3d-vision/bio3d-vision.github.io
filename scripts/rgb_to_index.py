import os
import random

import numpy as np
import tifffile as tif

from typing import Optional

def platelet_em_default_indexing():
    
    platelet_em_rgb_to_index = {
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
    return {'rgb_to_index': platelet_em_rgb_to_index,
            'index_to_class': platelet_em_index_to_class}

def rgb_to_index_semantic(rgb: np.ndarray,
                          color_map: Dict[Tuple[int, int, int], int]) -> np.ndarray:
    """

    Args:
        rgb:
        color_map:

    Returns:

    """
    def f_rgb(color: np.ndarray):
        cr, cg, cb = color.astype(np.int)
        return color_map[(cr, cg, cb)]

    return np.apply_along_axis(f_rgb, -1, rgb)

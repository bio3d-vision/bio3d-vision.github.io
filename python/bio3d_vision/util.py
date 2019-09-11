"""Utility functions used in conjunction with the bio3d_vision package.

"""
import matplotlib.pyplot as plt
import numpy as np

from typing import Any, Dict, Sequence


def imshow(images: Sequence[np.ndarray],
           figsize: Sequence[int],
           plot_settings: Sequence[Dict[str, Any]],
           frame: bool = True) -> None:
    """

    Args:
        images:
        figsize:
        plot_settings:
        frame:

    Returns:

    """
    f, ax = plt.subplots(nrows=1, ncols=len(images), figsize=figsize)
    for i, row in enumerate(ax):
        row.imshow(images[i], **plot_settings[i], extent=(0, 1, 1, 0))
        row.axis('tight')
        if frame:
            row.get_xaxis().set_ticks([])
            row.get_yaxis().set_ticks([])
        else:
            row.axis('off')

    pass

---
layout: page
title: 'platelet-em'
---

The **platelet-em** dataset contains two 3D scanning electron microscope (EM) images of human platelets, as well as instance and semantic segmentations of those two image volumes.

This data has been reviewed by NIBIB, contains no PII or PHI, and is cleared for public release. All files use a multipage uint16 TIF format. A 3D image with size [Z, X, Y] is saved as Z pages of size [X, Y]. Image voxels are approximately 40x10x10 nm<sup>3</sup>. 

## Download

[Download images and labels](https://www.dropbox.com/s/lo6i7v2mc9z2wft/images-and-labels.zip?dl=1) (95.8 MB)

## Image files

![50-images.tif, Z=0](media/50-images.png)

The **platelet** image volumes were acquired by a [Gatan 3View](https://www.gatan.com/products/sem-imaging-spectroscopy/3view-system) serial block-face scanning electron microscope (SBF-SEM). 

Image files are: 

- **50-images.tif**, a 50x800x800 SBF-SEM image saved as a grayscale TIF.

- **24-images.tif**, a 24x800x800 SBF-SEM image saved as a grayscale TIF.

## Label files

Label TIF files assign a color to each voxel in a corresponding image file. The colors correspond to labels, either object classes for semantic labels or unique object ids for instance labels.

---

#### Semantic labels

![50-semantic.tif, Z=0](media/50-semantic.png)

Semantic label files classify each image voxel into one of seven classes, indexed from 0-6:

| Index | Color | Class name |
| --- | --- |
| 0 | None | Background |
| 1 | Dark Blue | Cell |
| 2 | Cyan | Mitochondria |
| 3 | Green | Alpha granule |
| 4 | Yellow | Canalicular vessel |
| 5 | Red | Dense granule body |
| 6 | Purple | Dense granule core |

Semantic label files are:

- **50-semantic.tif**: A 50x800x800 semantic segmentation of _50-images.tif_, saved as an RGB TIF.

- **24-semantic.tif**: A 24x800x800 semantic segmentation of _24-images.tif_, saved as an RGB TIF.

---

#### Instance labels

![50-instance-cell-2d.tif, Z=0](media/50-instance-cell.png)

![50-instance-organelle-2d.tif, Z=0](media/50-instance-organelle.png)

Instance labels are separated into two label files per image: cell and organelle. _Cell_ instance labels assign a unique id to each cell in an image volume. _Organelle_ instance labels assign a unique id to each organelle in an image volume. 

IDs are assigned to distinct objects within the entire 3D image volume. Tags for cross-sections of the same 3D object are the same between different 2D image windows.

Instance label files are:

- **50-instance-cell.tif**: A 50x800x800 instance segmentation of cells in _50-images.tif_, saved as an RGB TIF.

- **50-instance-organelle.tif**: A 50x800x800 instance segmentation of organelles in _50-images.tif_, saved as an RGB TIF.

- **24-instance-cell.tif**: A 24x800x800 instance segmentation of cells in _24-images.tif_, saved as an RGB TIF.

- **24-instance-organelle.tif**: A 24x800x800 instance segmentation of organelles in _24-images.tif_, saved as an RGB TIF.
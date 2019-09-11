"""Borrowed from torch vision."""
import os
import os.path
import hashlib
import gzip
import errno
import tarfile
from tqdm import tqdm
import zipfile

from .rgb_to_index import convert_platelet_files


# Last updated 00:28 11 September 2019
PLATELET_EM_INFO = {
    'url': "https://www.dropbox.com/s/lo6i7v2mc9z2wft/images-and"
           "-labels.zip?dl=1",
    'filename': 'platelet-em.zip',
    'md5': 'e3a7bb0b0099220781bfea3e5ee9430c',
    'filedirs': ['images', 'labels-semantic', 'labels-instance']}


def download_if_needed(
        dataset_name: str,
        download_dir: str,
        convert_labels_to_indexed: bool = False):
    """Download a named dataset from the bio3d-vision collection.

    If specified, convert any appropriate dataset label files from an RGB
    image to an indexed image, a representation more suited to machine
    learning applications.

    Args:
        dataset_name:
        download_dir:
        convert_labels_to_indexed:

    Returns: None

    """
    # Currently only the 'platelet-em' dataset is available
    if dataset_name == 'platelet-em':
        dataset_info = PLATELET_EM_INFO
        convert_label_files = convert_platelet_files
    else:
        raise ValueError(f"Dataset name {dataset_name} not recognized. "
                         f"Possible choices are: 'platelet-em'.")

    dataset_dir = os.path.join(download_dir, dataset_name)
    if os.path.exists(dataset_dir):
        print(f'Found {dataset_name} dataset already in {download_dir}.')
    else:
        print(f'No {dataset_name} dataset found, downloading...')
        download_and_extract(
            dataset_info['url'],
            download_dir,
            filename=dataset_info['filename'],
            md5=dataset_info['md5'])

        if convert_labels_to_indexed:
            print('Converting dataset label file TIFs from RGB to indexed.')
            convert_label_files(dataset_dir)

    pass


def gen_bar_updater():
    pbar = tqdm(total=None)

    def bar_update(count, block_size, total_size):
        if pbar.total is None and total_size:
            pbar.total = total_size
        progress_bytes = count * block_size
        pbar.update(progress_bytes - pbar.n)

    return bar_update


def calculate_md5(fpath, chunk_size=1024 * 1024):
    md5 = hashlib.md5()
    with open(fpath, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            md5.update(chunk)
    return md5.hexdigest()


def check_md5(fpath, md5, **kwargs):
    return md5 == calculate_md5(fpath, **kwargs)


def check_integrity(fpath, md5=None):
    if not os.path.isfile(fpath):
        return False
    if md5 is None:
        return True
    return check_md5(fpath, md5)


def makedir_exist_ok(dirpath):
    """
    Python2 support for os.makedirs(.., exist_ok=True)
    """
    try:
        os.makedirs(dirpath)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise


def download_url(url, root, filename=None, md5=None):
    """Download a file from a url and place it in root.

    Args:
        url (str): URL to download file from
        root (str): Directory to place downloaded file in
        filename (str, optional): Name to save the file under. If None, use the basename of the URL
        md5 (str, optional): MD5 checksum of the download. If None, do not check
    """
    from six.moves import urllib

    root = os.path.expanduser(root)
    if not filename:
        filename = os.path.basename(url)
    fpath = os.path.join(root, filename)

    makedir_exist_ok(root)

    # downloads file
    if check_integrity(fpath, md5):
        print('Using downloaded and verified file: ' + fpath)
    else:
        try:
            print('Downloading ' + url + ' to ' + fpath)
            urllib.request.urlretrieve(
                url, fpath,
                reporthook=gen_bar_updater()
            )
        except (urllib.error.URLError, IOError) as e:
            if url[:5] == 'https':
                url = url.replace('https:', 'http:')
                print('Failed download. Trying https -> http instead.'
                      ' Downloading ' + url + ' to ' + fpath)
                urllib.request.urlretrieve(
                    url, fpath,
                    reporthook=gen_bar_updater()
                )
            else:
                raise e


def _is_tar(filename):
    return filename.endswith(".tar")


def _is_targz(filename):
    return filename.endswith(".tar.gz")


def _is_gzip(filename):
    return filename.endswith(".gz") and not filename.endswith(".tar.gz")


def _is_zip(filename):
    return filename.endswith(".zip")


def extract_archive(from_path, to_path=None, remove_finished=True):
    if to_path is None:
        to_path = os.path.dirname(from_path)

    if _is_tar(from_path):
        with tarfile.open(from_path, 'r') as tar:
            tar.extractall(path=to_path)
    elif _is_targz(from_path):
        with tarfile.open(from_path, 'r:gz') as tar:
            tar.extractall(path=to_path)
    elif _is_gzip(from_path):
        to_path = os.path.join(to_path, os.path.splitext(os.path.basename(from_path))[0])
        with open(to_path, "wb") as out_f, gzip.GzipFile(from_path) as zip_f:
            out_f.write(zip_f.read())
    elif _is_zip(from_path):
        with zipfile.ZipFile(from_path, 'r') as z:
            z.extractall(to_path)
    else:
        raise ValueError("Extraction of {} not supported".format(from_path))

    if remove_finished:
        os.remove(from_path)


def download_and_extract(url, 
                         download_root,
                         filename = None,
                         md5 = None, 
                         remove_finished = True):

    download_root = os.path.expanduser(download_root)
    download_root = os.path.join(download_root, 'platelet-em')
    os.makedirs(download_root, exist_ok=True)
    if not filename:
        filename = os.path.basename(url)

    download_url(url, download_root, filename, md5)

    archive = os.path.join(download_root, filename)
    print("Extracting {} to {}".format(archive, download_root))
    extract_archive(archive, download_root, remove_finished)

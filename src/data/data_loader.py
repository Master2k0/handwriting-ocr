# Copyright 2020 Břetislav Hájek <info@bretahajek.com>
# Licensed under the MIT License. See LICENSE for details.
from abc import ABCMeta, abstractmethod
import getpass
import os
from pathlib import Path
import sys
import tarfile
import urllib.request
import zipfile

import gdown
from tqdm import tqdm


DATA_FOLDER = Path(__file__).parent.joinpath("../../data/")


class Progressbar(tqdm):
    """Helper class for download progressbar."""

    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_url(url, output, username=None, password=None):
    """Download file from URL to output location.

    Args:
        url (str): URL for downloading the file
        output (Path): Path where should be downloaded file stored
        username (str): (optional) username for authentication
        password (str): (optional) username for authentication

    Returns:
        status (int): Returns status of download (200: OK, 401: Unauthorized,
            -1: Unknown)
    """

    if "drive.google.com" in url:
        gdown.download(url, str(output), quiet=False)
        return

    for _ in range(3):
        if username or password:
            # create a password manager
            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, url, username, password)
            handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
            # create "opener"
            opener = urllib.request.build_opener(handler)
            urllib.request.install_opener(opener)

        with Progressbar(
            unit="B", unit_scale=True, miniters=1, desc=url.split("/")[-1]
        ) as t:
            try:
                urllib.request.urlretrieve(url, filename=output, reporthook=t.update_to)
                return 200
            except urllib.error.HTTPError as e:
                if hasattr(e, "code") and e.code == 401:
                    return 401
                else:
                    print(f"\nError occured during download:\n{e}")
                    return -1


def file_extract(file_path, out_path):
    """Extract archive file into given location.

    Args:
        file_path (Path): path of archive file
        out_path (Path): path of folder where should be the file extracted
    """
    print(f"Extracting {file_path} file...")
    if file_path.suffix == ".zip":
        open_file = lambda x: zipfile.ZipFile(x, "r")
    elif file_path.suffix in [".gz", ".tgz", ".tar"]:
        open_file = lambda x: tarfile.open(x, "r:gz")

    with open_file(file_path) as data_file:
        data_file.extractall(out_path)


class Data(metaclass=ABCMeta):
    """Abstract class for managing data.

    Attributes:
        files (List[Tuple[str, str, str, str]]): List of datasets' files/folders (URL,
            tmp file, final file or folder, dataset type folder)
        require_auth (bool): if authentication is required (default = False)
        username (str): (optional) username for authentication during donwload
        password (str): (optional) password for authentication during donwload
    """

    require_auth = False
    username, password = None, None

    @property
    @abstractmethod
    def files(self):
        ...

    @abstractmethod
    def load(self, data_path):
        pass

    def is_downloaded(self, data_path):
        for _, _, res, folder in self.files:
            if not data_path.joinpath(folder, self.name, res).exists():
                return False
        return True

    def download(self, data_path):
        print(f"Collecting dataset {self.name}...")
        for url, f, res, folder in self.files:
            folder = data_path.joinpath(folder, self.name)
            tmp_output = folder.joinpath(f)
            res_output = folder.joinpath(res)
            if not res_output.exists():
                tmp_output.parent.mkdir(parents=True, exist_ok=True)
                # Try the authentication 3 times
                for i in range(3):
                    if self.require_auth:
                        if not self.username:
                            self.username = input(f"Username for {self.name} dataset: ")
                        if not self.password:
                            self.password = getpass.getpass(
                                f"Password for {self.name} dataset: "
                            )
                    status = download_url(url, tmp_output, self.username, self.password)
                    if status == 200:
                        break
                    elif status == 401 and i < 2:
                        print("Invalid username or password, please try again.")
                    else:
                        print(f"Dataset {self.name} skipped.")
                        return

                if tmp_output.suffix in [".zip", ".gz", ".tgz", ".tar"]:
                    file_extract(tmp_output, res_output)
                    tmp_output.unlink()


class Breta(Data):
    """Handwriting data from Břetislav Hájek."""

    files = [
        (
            "https://drive.google.com/uc?id=1p7tZWzK0yWZO35lipNZ_9wnfXRNIZOqj",
            "data.zip",
            "",
            "raw",
        ),
        (
            "https://drive.google.com/uc?id=1y6Kkcfk4DkEacdy34HJtwjPVa1ZhyBgg",
            "data.zip",
            "",
            "processed",
        ),
    ]

    def __init__(self, name="breta"):
        self.name = name

    def load(self, data_path):
        pass


class CVL(Data):
    """CVL Database
    More info at: https://zenodo.org/record/1492267#.Xob4lPGxXeR
    """

    files = [
        (
            "https://zenodo.org/record/1492267/files/cvl-database-1-1.zip",
            "cvl-database-1-1.zip",
            "",
            "raw",
        )
    ]

    def __init__(self, name="cvl"):
        self.name = name

    def load(self, data_path):
        pass


class IAM(Data):
    """IAM Handwriting Database
    More info at: http://www.fki.inf.unibe.ch/databases/iam-handwriting-database
    """

    require_auth = True
    files = [
        (
            "http://www.fki.inf.unibe.ch/DBs/iamDB/data/ascii/lines.txt",
            "lines.txt",
            "lines.txt",
            "raw",
        ),
        (
            "http://www.fki.inf.unibe.ch/DBs/iamDB/data/lines/lines.tgz",
            "lines.tgz",
            "lines",
            "raw",
        ),
    ]

    def __init__(self, name="iam", username=None, password=None):
        self.name = name
        self.username = username
        self.password = password

    def load(self, data_path):
        pass


class ORAND(Data):
    """ORAND CAR 2014 dataset
    More info at: https://www.orand.cl/icfhr2014-hdsr/#datasets
    """

    files = [
        (
            "https://www.orand.cl/orand_car/ORAND-CAR-2014.tar.gz",
            "ORAND-CAR-2014.tar.gz",
            "",
            "raw",
        )
    ]

    def __init__(self, name="orand"):
        self.name = name

    def load(self, data_path):
        pass


class Camb(Data):
    """Cambridge Handwriting Database
    More info at: ftp://svr-ftp.eng.cam.ac.uk/pub/data/handwriting_databases.README
    """

    files = [
        (
            "ftp://svr-ftp.eng.cam.ac.uk/pub/data/handwriting_databases.README",
            "handwriting_databases.README",
            "handwriting_databases.README",
            "raw",
        ),
        ("ftp://svr-ftp.eng.cam.ac.uk/pub/data/lob.tar", "lob.tar", "lob", "raw"),
        (
            "ftp://svr-ftp.eng.cam.ac.uk/pub/data/numbers.tar",
            "numbers.tar",
            "numbers",
            "raw",
        ),
    ]

    def __init__(self, name="camb"):
        self.name = name

    def load(self, data_path):
        pass


if __name__ == "__main__":
    datasets = [Breta(), CVL(), IAM(), ORAND(), Camb()]
    for d in datasets:
        d.download(DATA_FOLDER)

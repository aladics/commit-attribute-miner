import pickle

from github import Github
from dotenv import load_dotenv
from os import getenv
from typing import Any
from pathlib import Path
import requests

GH_ACCESS_TOKEN_KEY = "GITHUB_ACCESS_TOKEN"


def read_file_as_bytes(file_path: str | Path, encode_str: str | None = None) -> bytes:
    file_path = Path(file_path)
    with file_path.open("r") as fp:
        src_file = fp.read()

    if encode_str:
        file_bytes = src_file.encode(encode_str)
    else:
        file_bytes = src_file.encode()

    return file_bytes


def save_commit2vec_file(path: Path, content: bytes | None):
    if content:
        with path.open("wb") as fp:
            fp.write(content)


def get_file_content_from_url(url_: str) -> bytes | None:
    resp = requests.get(url_)
    if resp.status_code == 200:
        return requests.get(url_).content

    return None


def parse_proc_stdout(str_: str) -> float:
    return float(str_.split()[11])


def get_last_changed_dir(dir_path: Path) -> Path:
    return sorted(p for p in dir_path.iterdir() if p.is_dir())[-1]


def get_resolved_path(path_: Path) -> str:
    return str(path_.resolve())


def create_dextend_codes(codes: str):
    dextend_codes = []
    for code in codes:
        dextend_codes.append(['added _ code removed _ code'] * len(code))

    return dextend_codes


def enclose_separators_with_spaces(str_: str) -> str:
    separators = [".", "_", ",", ";", "-", ":", "(", ")", "[", "]", "{", "}"]
    for char in separators:
        str_ = str_.replace(char, f" {char} ").strip()

    return str_


def remove_whitespaces(list_: list[str]) -> list[str]:
    return [" ".join(elem.split()) for elem in list_]


def prepare_cc2vec_input(list_: list[str]) -> list[str]:
    return remove_whitespaces([enclose_separators_with_spaces(el) for el in list_])


def get_lines_from_patch(src: str, prefix: str) -> list[str]:
    return [line.strip().removeprefix(prefix).strip() for line in src.split("\n") if line.strip().startswith(prefix)
            and line.strip().removeprefix(prefix).strip() != ""]


def get_github_access_token() -> str:
    load_dotenv()
    return getenv(GH_ACCESS_TOKEN_KEY)


def get_github_instance() -> Github:
    return Github(get_github_access_token())


def save_pickle(data: Any, save_path: Path) -> None:
    """

    :rtype: object
    """
    with save_path.open("wb") as fp:
        pickle.dump(data, fp)

from dataclasses import dataclass, field
import logging
from pathlib import Path
import re

from github.File import File
from github.Commit import Commit

from util import get_lines_from_patch, prepare_cc2vec_input, get_file_content_from_url, save_commit2vec_file
from config import Config, get_config
from cache import Cache, get_cache

logging.basicConfig(format="%(asctime)s [%(levelname)s]| %(message)s", datefmt="%m-%d %H:%M:%S")


class GHAccessException(Exception):
    pass


@dataclass
class GHFile:
    gh_file: File

    def get_removed_code(self) -> list[str]:
        if not self.gh_file.patch:
            return []
        return prepare_cc2vec_input(get_lines_from_patch(self.gh_file.patch, "-"))

    def get_added_code(self) -> list[str]:
        if not self.gh_file.patch:
            return []
        return prepare_cc2vec_input(get_lines_from_patch(self.gh_file.patch, "+"))

    def get_changed_line_indexes(self):
        """
        Get the changed lines positions in the form of (start_pos, end_pos)
        :return:
        """
        patch = self.gh_file.patch
        matches = re.findall("@@ -(\d+),(\d+) \+(\d+),(\d+) @@", patch)
        positions = []
        for match in matches:
            old_positions = (int(match[0]), int(match[0]) + int(match[1]))
            new_positions = (int(match[2]), int(match[2]) + int(match[3]))
            positions.append(new_positions)

        return positions

    def get_path(self) -> str:
        return str(Path(self.gh_file.filename))

    def get_pre_commit_path(self) -> str:
        path = self.gh_file.previous_filename
        if not self.gh_file.previous_filename:
            path = self.gh_file.filename

        path = Path(path)
        return str(path)

    def get_filename(self) -> str:
        return Path(self.gh_file.filename).name

    def get_pre_commit_url(self, parent_commit_sha: str) -> str:
        if self.gh_file.previous_filename is not None:
            previous_filename = self.gh_file.previous_filename
        else:
            previous_filename = self.gh_file.filename
        pre_state_file_path = f"{parent_commit_sha}/{previous_filename}"
        raw_url_prefix = self.gh_file.raw_url[:self.gh_file.raw_url.find("raw") + 3]
        return f"{raw_url_prefix}/{pre_state_file_path}"

    def get_pre_commit_state(self, commit: Commit) -> bytes | None:
        """
        Get the contents of the file before the commit. If the file was created in this commit, None is returned.
        :param commit: The commit that contains this file
        :return: The pre-commit state of the file in bytes, or None if there is no pre-commit state
        """
        if not commit.parents:
            return None

        pre_commit_url = self.get_pre_commit_url(commit.parents[0].sha)
        return get_file_content_from_url(pre_commit_url)

    def get_post_commit_state(self) -> bytes | None:
        return get_file_content_from_url(self.gh_file.raw_url)

    def get_url(self) -> str:
        return self.gh_file.raw_url


@dataclass
class CommitAttributes:
    hash: str
    files: list[GHFile]
    message: str

    def get_files_cc2vec_flattened(self) -> list[dict[str, list[str]]]:
        return [{"added_code": file.get_added_code(), "removed_code": file.get_removed_code()} for file in self.files]


@dataclass
class GHCommit:
    repo: str
    sha: str
    label: str

    files: list[GHFile] = field(init=False)
    cache: Cache = field(init=False)
    config: Config = field(init=False)

    def safe_load_files(self) -> None:
        """
        Load the files in the commit only if they are not loaded yet
        :return: None
        """
        if not hasattr(self, 'files'):
            self.load_files()

    def load_files(self) -> None:
        """
        Load the files in the commit
        :return: None
        """
        self.files = []
        files = self.get_filtered_commit_files()
        for file in files:
            if not file.patch:
                continue

            self.files.append(GHFile(file))

    def __post_init__(self):
        self.config = get_config()
        self.cache = get_cache()

    def get_filtered_commit_files(self) -> list[File]:
        """
        :return: filtered list of commit files based on the filtering specified in the config
        """
        commit = self.cache.get_commit(self.repo, self.sha)
        files = [file for file in commit.files if any(file.filename.endswith(file_type) for file_type in
                                                      self.config.file_types)][:self.config.max_files]

        return files

    def get_raw_commit(self) -> Commit:
        return self.cache.get_commit(self.repo, self.sha)

    def get_parent(self) -> Commit:
        """
        Get the parent commit
        :return: Commit object
        """
        return self.cache.get_commit(self.repo, self.sha).parents[0]

    def get_message(self) -> str:
        """
        Get the commit message
        :return: Commit message as string
        """
        commit = self.cache.get_commit(self.repo, self.sha)
        return commit.commit.message

    def get_attributes(self) -> CommitAttributes | None:
        self.safe_load_files()
        return CommitAttributes(self.sha, self.files, self.get_message())

    def get_commit2vec_files_path(self, path_: str) -> Path:
        """
        Get the path to where the commit2vec files will be saved for this commit
        :param path_: The root to all commit2vec files
        :return: Path object for the directory of commit2vec file pairs
        """
        repo_str = self.repo.replace('/', '_')
        commit2vec_files_path = Path(path_) / f"{repo_str}_{self.sha}"
        commit2vec_files_path.mkdir(parents=True, exist_ok=True)

        return commit2vec_files_path

    def save_pre_post_files(self, path_: str) -> bool:
        """
        Save the pre and post versions of files, return if any pair was saved
        :param path_: The root to all commit2vec files
        :return: Boolean representing if any pre post was found
        """
        self.safe_load_files()
        commit2vec_files_path = self.get_commit2vec_files_path(path_)
        n_files = len(list(commit2vec_files_path.glob("*")))
        if n_files > 0:
            return True

        pair_found = False
        for file in self.files:
            pre_state = file.get_pre_commit_state(self.get_raw_commit())
            if not pre_state:
                continue
            post_state = file.get_post_commit_state()

            save_commit2vec_file(commit2vec_files_path / f"pre_{file.get_filename()}", pre_state)
            save_commit2vec_file(commit2vec_files_path / f"post_{file.get_filename()}", post_state)
            pair_found = True

        return pair_found

    def save_pre_post_files_pairs(self, path_: str | Path):
        """
        Save the pre and post versions of files but only if both states exists
        :return: None
        """
        self.safe_load_files()
        pair_found = self.save_pre_post_files(path_)

        if not pair_found:
            self.get_commit2vec_files_path(path_).rmdir()

    def get_parent_sha(self) -> str:
        return self.get_parent().sha

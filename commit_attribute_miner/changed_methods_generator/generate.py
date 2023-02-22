from dataclasses import dataclass
from pathlib import Path

from miner import get_projectkb_commits_top_1, get_mock_commits
from commit import GHCommit, GHFile
from changed_methods_generator.java_parser import get_methods_by_row_indicies, get_all_methods, \
    are_nodes_with_same_name, get_node_name
from tree_sitter import Node
from util import read_file_as_bytes


@dataclass()
class ChangeMethodWriter:
    commit: GHCommit
    post_commit_method: Node
    pre_commit_method: Node
    file: GHFile
    result_file: Path

    def __post_init__(self):
        if not self.result_file.exists():
            self.init_result_file()

    def init_result_file(self):
        header = "Repository,Before state URL,After state URL,Before state file path,After state file path," \
                 "Before state line:col,After state line:col,Method name,Before state commit hash,After state commit " \
                 "hash "

        with self.result_file.open("w") as fp:
            fp.write(header)

    def get_result_row(self) -> str:
        repo = self.commit.repo
        pre_url = self.file.get_pre_commit_url(self.commit.get_parent_sha())
        post_url = self.file.get_url()
        pre_path = self.file.get_pre_commit_path()
        post_path = self.file.get_path()
        pre_line_col = f"{self.pre_commit_method.start_point[0]+1}:{self.pre_commit_method.start_point[1]+1}"
        post_line_col = f"{self.post_commit_method.start_point[0]+1}:{self.post_commit_method.start_point[1]+1}"
        method_name = get_node_name(self.pre_commit_method)
        pre_commit_sha = self.commit.get_parent_sha()
        post_commit_sha = self.commit.sha

        return f"{repo},{pre_url},{post_url},{pre_path},{post_path},{pre_line_col},{post_line_col},{method_name}," \
               f"{pre_commit_sha},{post_commit_sha}\n"

    def append_to_result(self):
        result_row = self.get_result_row()
        pass


def generate_method_pairs_for_commits(commits_: list[GHCommit]):
    """
    Generate the pairs of pre and pos commit states of methods for a list of commits
    :param commits_: The list of commits to analyze
    :return: None
    """
    for commit in commits_:
        commit.load_files()
        for file in commit.files:
            pre_commit_file = file.get_pre_commit_state(commit.get_raw_commit())
            if not pre_commit_file:
                # we want pairs, so a missing a pre-state makes the file unfit
                continue

            pre_commit_file = pre_commit_file

            changed_line_positions = file.get_changed_line_indexes()
            post_commit_file = file.get_post_commit_state()
            changed_methods = get_methods_by_row_indicies(post_commit_file,
                                                          changed_line_positions)
            all_pre_commit_methods = get_all_methods(pre_commit_file)

            for post_change_method in changed_methods:
                pre_commit_method = next((method for method in all_pre_commit_methods if
                                          are_nodes_with_same_name(method, post_change_method)), None)

                if not pre_commit_method:
                    continue

                result_writer = ChangeMethodWriter(commit, post_change_method, pre_commit_method, file, Path(""))
                result_writer.append_to_result()


if __name__ == "__main__":
    commits = get_mock_commits()
    generate_method_pairs_for_commits(commits)
    pass

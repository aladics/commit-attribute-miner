from commit import GHCommit
import yaml
from config import get_config
from pathlib import Path
from util import save_pickle, create_dextend_codes
from random import shuffle

CONFIG = get_config()


def get_repo_from_url(url_str: str) -> str:
    repo_url_path = Path(url_str)
    if "git-wip-us.apache.org" in url_str or "git.apache.org" in url_str:
        return "/".join(["apache", repo_url_path.stem])
    if url_str.endswith('.git'):
        repo_url_path = Path(url_str.replace('.git', ''))

    return "/".join([repo_url_path.parts[-2], repo_url_path.parts[-1]])


def get_projectkb_commits_top_1() -> list[GHCommit]:
    """
    Parse the projectkb database by only considering the first introducing commits.
    :return:
    """
    commits = []
    with Path(CONFIG.src_dataset_path).open() as fp:
        project_kb_dict = yaml.safe_load(fp)

    for cve_id, vuln_data in project_kb_dict.items():
        introducer_data = list(vuln_data['commitsWithIntroducers'].items())[0]
        repo = get_repo_from_url(vuln_data['repo'])

        fixing_commit = GHCommit(repo, introducer_data[0], "0")
        introducing_commit = GHCommit(repo, introducer_data[1][0], "1")
        commits.append(fixing_commit)
        commits.append(introducing_commit)

    return commits


def get_projectkb_commits() -> list[GHCommit]:
    commits = []
    with Path(CONFIG.src_dataset_path).open() as fp:
        project_kb_dict = yaml.safe_load(fp)

    for cve_id, vuln_data in project_kb_dict.items():
        introducer_data = list(vuln_data['commitsWithIntroducers'].items())[0]
        repo = get_repo_from_url(vuln_data['repo'])

        fixing_commit = GHCommit(repo, introducer_data[0], "0")
        commits.append(fixing_commit)

        introducing_commits = [GHCommit(repo, sha, "1") for sha in introducer_data[1]]
        commits.extend(introducing_commits)
        continue
    return commits


def get_mock_commits() -> list[GHCommit]:
    return [GHCommit(get_repo_from_url("https://github.com/igniterealtime/Openfire"),
                     "6088e21ca06fb62790d9ea02faf8c884302e0cd9", 0),
            GHCommit(get_repo_from_url("https://github.com/apache/struts"), "e05d71ba329337ba63784555fbbe9bb8e0290543",
                     1)]


def get_cc2vec_attributes(commits: list[GHCommit]) -> tuple[list[str], list[str], list[str], dict[str, list[str]]]:
    """
    Get the attributes for a list a commits in a way that CC2VEC can be trained on the features
    :return: tuple[commits_ids, commit_labels, commit_messages, commit_codes]
    """
    ids = []
    labels = []
    messages = []
    codes = []

    for commit_ in commits:
        attributes = commit_.get_attributes()
        file_modifications = attributes.get_files_cc2vec_flattened()
        if not file_modifications:
            continue

        messages.append(" ".join(attributes.message.split()))
        codes.append(file_modifications)
        labels.append(int(commit_.label))
        ids.append(commit_.sha)

    return ids, labels, messages, codes


def shuffle_lists(*lists):
    l = list(zip(*lists))

    shuffle(l)
    return zip(*l)


def split_to_train_test_cc2vec(attributes: tuple[list[str], list[str], list[str], dict[str, list[str]]]) -> \
        tuple[tuple[list[str], list[str], list[str], dict[str, list[str]]],
              tuple[list[str], list[str], list[str], dict[str, list[str]]]]:
    shuffled_ids, shuffled_labels, shuffled_messages, shuffled_codes = shuffle_lists(*attributes)
    split_pos = int(len(shuffled_ids) * CONFIG.train_test_ratio)

    train_set = (list(shuffled_ids[:split_pos]), list(shuffled_labels[:split_pos]),
                 list(shuffled_messages[:split_pos]), list(shuffled_codes[:split_pos]))
    test_set = (list(shuffled_ids[split_pos:]), list(shuffled_labels[split_pos:]),
                list(shuffled_messages[split_pos:]), list(shuffled_codes[split_pos:]))
    return train_set, test_set


if __name__ == '__main__':
    cc2vec_attributes = get_cc2vec_attributes(get_projectkb_commits())
    save_pickle(cc2vec_attributes, Path(CONFIG.data_path))

    train_set, test_set = split_to_train_test_cc2vec(cc2vec_attributes)
    save_pickle(train_set, Path(CONFIG.data_train_path))
    save_pickle(test_set, Path(CONFIG.data_test_path))

    dextend_codes_train = create_dextend_codes(train_set[3])
    save_pickle((train_set[0], train_set[1], train_set[2], dextend_codes_train), Path(CONFIG.data_dextend_train_path))

    dextend_codes_test = create_dextend_codes(test_set[3])
    save_pickle((test_set[0], test_set[1], test_set[2], dextend_codes_test), Path(CONFIG.data_dextend_test_path))

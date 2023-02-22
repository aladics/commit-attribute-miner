from dataclasses import dataclass
from pathlib import Path
import pickle
import logging
import time

from github import Github
from github.Repository import Repository
from github.Commit import Commit
from github.GithubException import GithubException, RateLimitExceededException

from config import get_config
from util import get_github_instance


logging.basicConfig(format="%(asctime)s [%(levelname)s]| %(message)s", datefmt="%m-%d %H:%M:%S")


def sanitize_path(raw_repo: str):
    return raw_repo.replace("/", "_")


@dataclass
class Cache:
    gh_access: Github
    root_path: Path = None

    def __post_init__(self):
        config = get_config()
        if self.root_path is None:
            self.root_path = Path(config.cache_path)

    def get_cached_repo_path(self, repo: str) -> tuple[Path, Path]:
        repo_path = self.root_path / sanitize_path(repo)
        repo_pkl_path = repo_path / f"{sanitize_path(repo)}.pkl"

        return repo_path, repo_pkl_path

    def get_repo(self, repo: str) -> Repository | None:
        repo_path, repo_pkl_path = self.get_cached_repo_path(repo)
        if repo_path.exists():
            with repo_pkl_path.open("rb") as fp:
                repo_obj = pickle.load(fp)
        else:
            try:
                repo_obj = self.gh_access.get_repo(repo)
            except RateLimitExceededException:
                logging.error(f"Rate limit exceeded...Waiting 1 hr, then retrying")
                time.sleep(60*60)
                return self.get_repo(repo)
            except GithubException as ex:
                logging.error(f"Error retrieving repo {repo}: {ex}")
                return None

            repo_path.mkdir(parents=True, exist_ok=True)

            with repo_pkl_path.open("wb") as fp:
                pickle.dump(repo_obj, fp)

        return repo_obj

    def get_commit(self, repo: str, commit_hash: str) -> Commit | None:
        repo_path, _ = self.get_cached_repo_path(repo)

        commit_pkl_path = repo_path / f"{commit_hash}.pkl"

        if commit_pkl_path.exists():
            with commit_pkl_path.open("rb") as fp:
                commit_obj = pickle.load(fp)
        else:
            repo_obj = self.get_repo(repo)
            if repo_obj is None:
                return None
            try:
                commit_obj = repo_obj.get_commit(commit_hash)

                with commit_pkl_path.open("wb") as fp:
                    pickle.dump(commit_obj, fp)
            except RateLimitExceededException:
                logging.error(f"Rate limit exceeded...Waiting 1 hr, then retrying")
                time.sleep(60 * 60)
                return self.get_commit(repo, commit_hash)
            except GithubException as ex:
                logging.error(f"Error retrieving commit {commit_hash} from repo {repo}: {ex}")
                return None

        return commit_obj


def get_cache():
    return Cache(get_github_instance())

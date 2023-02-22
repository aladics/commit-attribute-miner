from miner import get_projectkb_commits_top_1

COMMIT2VEC_FILES_ROOT = "F:/work/kutatas/code_change_repr/compare_cgange_reprs/commit_attribute_miner/results/commit2vec"

if __name__ == "__main__":
    commits = get_projectkb_commits_top_1()
    for commit in commits:
        commit.save_pre_post_files_pairs(COMMIT2VEC_FILES_ROOT)
    pass

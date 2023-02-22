# Commit Attribute Miner

## Setup
Settings can be found in commit_attribute_miner/conf.yaml

## Xval cc2vec
Run 10 fold xval on cc2vec by running the ml module from the commit_attribute_miner directory:
python -m commit_attribute_miner.ml

## Generate files for commit2vec
Generate files for the first 10 files in each commit in the top-1-introducing commit per fixing commit database
pyton -m commit_attribute_miner.miner


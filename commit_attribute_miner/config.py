from pydantic import BaseModel
from pathlib import Path
import yaml


class Config(BaseModel):
    max_files: int
    file_types: list[str]
    cache_path: str
    src_dataset_path: str

    train_test_ratio: float
    data_path: str
    data_train_path: str
    data_test_path: str
    data_dextend_train_path: str
    data_dextend_test_path: str
    f1_scores_dir_path: str

    def adjust_file_types(self):
        if "any" in self.file_types:
            # change file_types to empty string, so every filename will satisfy as every string ends with an empty
            # string
            self.file_types = [""]

    def adjust_cache_root(self):
        if self.cache_path.lower() == "default":
            self.cache_path = str((Path(__file__).parent.parent / "cache").resolve())

    def adjust_self(self):
        self.adjust_file_types()
        self.adjust_cache_root()


def get_config(conf_path=None):
    if not conf_path:
        conf_path = Path(__file__).resolve().parent / "conf.yaml"

    with conf_path.open() as fp:
        conf = yaml.safe_load(fp)

    config = Config(**conf)
    config.adjust_self()
    return config



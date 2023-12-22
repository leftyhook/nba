import configparser

from os import path


class Config:
    def __init__(self, file_path: str):
        parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

        if not path.exists(file_path):
            raise FileNotFoundError(f"Config file {file_path} not found.")

        parser.read(file_path)
        section_dirs = parser["DIRS"]
        section_paths = parser["PATHS"]

        self.injury_report_dir = path.expandvars(section_dirs.get("injury_reports"))
        self.injury_report_path_latest = path.expandvars(section_paths.get("latest_injury_report", ""))

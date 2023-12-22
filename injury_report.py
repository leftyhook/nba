import sys
import argparse
import csv
import logging
import os
import requests

from datetime import datetime, timedelta

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTPage, LTTextContainer

import logger
import datetime_utils
from nba_config import Config

from io import BytesIO
from collections.abc import Iterator

TEAMS = {
    'ATL': 'Atlanta Hawks',
    'BOS': 'Boston Celtics',
    'BKN': 'Brooklyn Nets',
    'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls',
    'CLE': 'Cleveland Cavaliers',
    'DAL': 'Dallas Mavericks',
    'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons',
    'GSW': 'Golden State Warriors',
    'HOU': 'Houston Rockets',
    'IND': 'Indiana Pacers',
    'LAC': 'LA Clippers',
    'LAL': 'L.A. Lakers Lakers',
    'MEM': 'Memphis Grizzlies',
    'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks',
    'MIN': 'Minnesota Timberwolves',
    'NOP': 'New Orleans Pelicans',
    'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder',
    'ORL': 'Orlando Magic',
    'PHI': 'Philadelphia 76ers',
    'PHX': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers',
    'SAC': 'Sacramento Kings',
    'SAS': 'San Antonio Spurs',
    'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz',
    'WAS': 'Washington Wizards'
}

STATUSES = ['Questionable', 'Out', 'Probable', 'Doubtful', 'Available']

eastern_tz = datetime_utils.eastern_timezone()


def latest_report_date_time() -> datetime:
    today = datetime.now(tz=eastern_tz)
    hour = today.hour
    minute = today.minute

    if minute < 30:
        if hour == 0:
            hour = 23
            today = today - timedelta(days=1)
        else:
            hour = hour - 1

    return datetime(today.year, today.month, today.day, hour, minute=0)


def formatted_report_timestamp(dt: datetime) -> str:
    hour = dt.hour

    am_pm = "PM"
    if hour > 12:
        hour -= 12
    elif hour < 12:
        am_pm = "AM"
        if hour == 0:
            hour = 12

    return f"{dt.strftime('%Y-%m-%d')}_{str(hour).zfill(2)}{am_pm}"


class InjuryReport:
    def __init__(self, pdf_pages: Iterator[LTPage]):
        self.pdf_pages = pdf_pages
        # self.report_date = None
        # self.report_time = None
        # self.players = []
        # self.report_json = []
        # self.teams = {}

    @classmethod
    def build_from_file(cls, full_file_path: str):
        return cls(extract_pages(full_file_path))

    @classmethod
    def build_from_datetime(cls, dt: datetime, file_path: str = ""):
        if file_path:
            full_file_path = download_injury_report(file_path, dt)
            return cls.build_from_file(full_file_path)

        content = BytesIO(get_injury_report(dt))
        return cls(extract_pages(content))

    def dump_to_csv(self, file_path):
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, self.players[0].keys())
            writer.writeheader()
            writer.writerows(self.players)

    def timestamped_file_name(self):
        date_str = datetime.strptime(self.report_date, '%m/%d/%y').strftime('%Y%m%d')
        time_str = datetime.strptime(self.report_time, '%H:%M %p').strftime('%H%p')
        return f'NBAInjuryReport.{date_str}.{time_str}.csv'


def injury_report_url(date_time: datetime) -> str:
    date_time_tag = formatted_report_timestamp(date_time)
    return f'https://ak-static.cms.nba.com/referee/injury/Injury-Report_{date_time_tag}.pdf'


def injury_report_file_name(date_time: datetime) -> str:
    return f'NBAInjuryReport_{formatted_report_timestamp(date_time)}.pdf'


def get_injury_report(date_time: datetime) -> bytes:
    url = injury_report_url(date_time)
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.content
    else:
        resp.raise_for_status()


def download_injury_report(file_path, dt: datetime = latest_report_date_time()) -> str:
    # date_and_time needs to be in the format of '%Y-%m-%d_%H%p'"
    content = get_injury_report(dt)
    full_file_path = os.path.join(file_path, injury_report_file_name(dt))

    with open(full_file_path, 'wb') as out_file:
        out_file.write(content)

    return full_file_path


def parse_injury_report(pdf_file: str | BytesIO) -> list[list[str]]:
    """
    Have observed one time a case where matchup and team are squashed together into one textbox:
    <LTTextBoxHorizontal(31) 200.952,121.091,339.163,131.091 'MEM@HOU Memphis Grizzlies\n'>

    Parameters:
        pdf_file (str|BytesIO)

    Returns:
        list[list[str]]:
    """
    try:
        pdf_pages = extract_pages(pdf_file)
    except Exception as exc:
        logging.error("Error extracting pdf pages. Check that pdf_file is a valid file path or file-like object.")
        raise exc

    lines = []
    x0_set = set()

    for page_layout in pdf_pages:
        elements = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                elements.append(element)

        elements.sort(key=lambda x: x.y1, reverse=True)

        line = []
        for i in range(1, len(elements) - 1):
            line.append(elements[i])
            if len(lines) > 0:
                x0_set.add(elements[i].x0)

            if elements[i].y1 > elements[i + 1].y1 and elements[i].y0 > elements[i + 1].y0:
                line.sort(key=lambda x: x.x0, reverse=False)
                lines.append(line)
                # print(line)
                line = []

    x0_list = sorted(x0_set)

    game_date_tb = None
    game_time_tb = None
    matchup_tb = None
    team_tb = None

    for i in range(1, len(lines)):
        player_tb = None
        status_tb = None
        reason_tb = None
        for textbox in lines[i]:
            col_idx = x0_list.index(textbox.x0)
            if col_idx == 0:
                game_date_tb = textbox
                game_time_tb = None
                matchup_tb = None
                team_tb = None
            elif col_idx == 1:
                game_time_tb = textbox
                matchup_tb = None
                team_tb = None
            elif col_idx == 2:
                matchup_tb = textbox
                team_tb = None
            elif col_idx == 3:
                team_tb = textbox
            elif col_idx == 4:
                player_tb = textbox
            elif col_idx == 5:
                status_tb = textbox
            elif col_idx == 6:
                reason_tb = textbox

        lines[i] = [game_date_tb, game_time_tb, matchup_tb, team_tb, player_tb, status_tb, reason_tb]

    parsed_lines = []
    for line in lines:
        parsed_line = [
            None if textbox is None
            else textbox.get_text().strip().replace("\n", " ")
            for textbox in line
        ]
        if line[2].x1 > x0_list[3]:
            # The matchup and team textboxes have been squashed together. Need to split
            matchup = parsed_line[2][0:parsed_line[2].index(" ")]
            parsed_line[3] = parsed_line[2][len(matchup) + 1:]
            parsed_line[2] = matchup

        parsed_lines.append(parsed_line)
        print(parsed_line)

    return parsed_lines


def parse_args(args: list) -> argparse.Namespace:
    """
    Parse a list of command line arguments.

    Parameters:
        args (list): The list of command line arguments

    Returns:
        argparse.Namespace: The parsed arguments
    """
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="Full file path to ini config file.",
    )
    arg_parser.add_argument(
        "-l",
        "--log-level",
        type=str,
        required=False,
        default=logger.DEFAULT_LOG_LEVEL_STDOUT,
        choices=[
            logging.getLevelName(logging.DEBUG),
            logging.getLevelName(logging.INFO),
            logging.getLevelName(logging.WARNING),
            logging.getLevelName(logging.ERROR),
            logging.getLevelName(logging.CRITICAL)
        ],
        help=f"Log level. Defaults to {logger.DEFAULT_LOG_LEVEL_STDOUT}",
    ),
    arg_parser.add_argument(
        "-f",
        "--log-file",
        type=str,
        required=False,
        default=None,
        help=("Log file. If provided, the file name will be amended to include today's date. "
              "If omitted, logging will still write to stdout.")
    )
    return arg_parser.parse_args(args)


def main(cmd_line_args: list):
    """
    Main program. Downloads the latest injury report and parses it into a normalized csv file.

    We need to be able to do the following:
    1. Retrieve an injury report file from the web, and save it if we want
    2. Load an injury report from a file
    3. Parse the injury report into a normalized list.
    4. Save the normalized list to csv.
    5. Write the normalized list to database.
    6. Create an estimated injury report that reasonably predicts the content for teams that have
        'NOT YET SUBMITTED' their injury report early in the day. This would be considered the latest
        file, to be used as input for any game simulations. The 'estimated' report would be replaced
        with the regular injury report once all teams have submitted their injury statuses.

    :param cmd_line_args:
    :return:
    """
    try:
        parsed_args = parse_args(cmd_line_args)

        logger.configure_logging(parsed_args.log_level, parsed_args.log_file)
        logging.info("Running Python version %s" % sys.version)
        logging.info(
            "injury_report downloader/parser script started with command line arguments: %s" % str(cmd_line_args)
        )

        config = Config(parsed_args.config)
        injury_report_dir = config.injury_report_dir
        injury_report_path_latest = config.injury_report_path_latest

        # file_path = download_injury_report(injury_report_dir)
        # read_pdf(file_path)
        read_pdf("")

    except Exception as exc:
        logging.exception(exc)
        sys.exit(1)

    # file_path = "C:\\Users\\argue\\OneDrive\\LeftyHook\\NBA\\InjuryReports\\"
    # dump_csv = True

    # pdf_reader = download_injury_report(file_path, date_and_time, False)
    # if pdf_reader is not None:
    #     report = parse_injury_report(pdf_reader)
    #
    #     if date_and_time is None:
    #         full_file_path = os.path.join(file_path, "NBAInjuryReport.Latest.csv")
    #     else:
    #         full_file_path = os.path.join(file_path, f'{report.timestamped_file_name()}.csv')
    #
    #     if dump_csv:
    #         report.dump_to_csv(full_file_path)


if __name__ == "__main__":
    main(sys.argv[1:])

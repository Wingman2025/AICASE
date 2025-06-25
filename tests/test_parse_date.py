import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

import db_utils


def test_parse_month_and_year():
    assert db_utils.parse_date("July 2024") == "2024-07-01"


def test_parse_month_and_year_case_insensitive():
    assert db_utils.parse_date("july 2024") == "2024-07-01"


def test_parse_another_month():
    assert db_utils.parse_date("March 2025") == "2025-03-01"

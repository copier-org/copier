import copier
from copier.config.user_data import load_logfile_data

from .helpers import PROJECT_TEMPLATE

SRC = f"{PROJECT_TEMPLATE}_logfile"


def test_logfile(dst):
    """Test copier behaves properly when using a logfile."""
    round_file = dst / "round.txt"

    # Check 1st round is properly executed and remembered
    copier.copy(SRC, dst, force=True)
    assert round_file.read_text() == "It's the 1st round.\n"
    log = load_logfile_data(dst)
    assert log["round"] == "1st"

    # Check 2nd round is properly executed and remembered
    copier.copy(SRC, dst, {"round": "2nd"}, force=True)
    assert round_file.read_text() == "It's the 2nd round.\n"
    log = load_logfile_data(dst)
    assert log["round"] == "2nd"

    # Check repeating 2nd is properly executed and remembered
    copier.copy(SRC, dst, force=True)
    assert round_file.read_text() == "It's the 2nd round.\n"
    log = load_logfile_data(dst)
    assert log["round"] == "2nd"

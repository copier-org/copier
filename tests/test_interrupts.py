from unittest.mock import patch

import pytest
import yaml

from copier import Worker
from copier.errors import CopierAnswersInterrupt

from .helpers import build_file_tree


@pytest.mark.parametrize(
    "questions, side_effect, raises",
    (
        (
            {
                "question": {"type": "str"},
            },
            # We override the prompt method from questionary to raise this
            # exception and expect our surrounding machinery to re-raise
            # it as a CopierAnswersInterrupt.
            KeyboardInterrupt,
            CopierAnswersInterrupt,
        ),
        (
            {
                "question": {"type": "str"},
            },
            KeyboardInterrupt,
            KeyboardInterrupt,
        ),
    ),
)
def test_keyboard_interrupt(tmp_path_factory, questions, side_effect, raises):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": yaml.safe_dump(questions),
        }
    )
    worker = Worker(str(src), dst, defaults=False)

    with patch("copier.main.unsafe_prompt", side_effect=side_effect):
        with pytest.raises(raises):
            worker.run_copy()


@pytest.mark.parametrize(
    "questions, side_effects, answers",
    (
        (
            {
                "question1": {"type": "str"},
                "question2": {"type": "str"},
                "question3": {"type": "str"},
            },
            [
                {"question1": "foobar"},
                {"question2": "yosemite"},
                KeyboardInterrupt,
            ],
            {
                "question1": "foobar",
                "question2": "yosemite",
            },
        ),
    ),
)
def test_multiple_questions_interrupt(
    tmp_path_factory, questions, side_effects, answers
):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": yaml.safe_dump(questions),
        }
    )
    worker = Worker(str(src), dst, defaults=False)

    with patch("copier.main.unsafe_prompt", side_effect=side_effects):
        with pytest.raises(CopierAnswersInterrupt) as err:
            worker.run_copy()
        assert err.value.answers.user == answers
        assert err.value.template == worker.template

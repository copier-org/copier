import pytest

from copier.tools import prompt, prompt_bool


def test_prompt(stdin, capsys):
    """Test basic prompt functionality"""
    question = "What is your name?"
    name = "Inigo Montoya"

    stdin.append(name + "\n")
    response = prompt(question)

    stdout, _ = capsys.readouterr()
    assert response == name
    assert stdout == question + " "


def test_prompt_no_response(stdin, capsys):
    """Prompts with no response should ask again"""
    question = "What is your name?"
    name = "Inigo Montoya"

    stdin.append("\n" + name + "\n")
    response = prompt(question, default="")

    stdout, _ = capsys.readouterr()
    assert response == name
    assert stdout == (question + " ") * 2


def test_prompt_no_response_default_None(stdin, capsys):
    """Prompts with no response should ask again"""
    question = "What is your name?"

    stdin.append("\n")
    response = prompt(question, default=None)

    stdout, _ = capsys.readouterr()
    assert response is None
    assert stdout == (question + " ")


def test_prompt_default_no_input(stdin, capsys):
    question = "What is your name?"
    default = "The Nameless One"

    stdin.append("\n")
    response = prompt(question, default=default)

    out, _ = capsys.readouterr()
    assert response == default
    assert out == "{} [{}] ".format(question, default)


def test_prompt_default_overridden(stdin, capsys):
    question = "What is your name?"
    default = "The Nameless One"
    name = "Buttercup"

    stdin.append(name + "\n")
    response = prompt(question, default=default)

    out, _ = capsys.readouterr()
    assert response == name
    assert out == "{} [{}] ".format(question, default)


def test_prompt_error_message(stdin, capsys):
    question = "Is this awesome?"
    error = "You know that is not correct"

    def validator(value):
        if value != "yes":
            raise ValueError(error)
        return True

    stdin.append("no\n")
    stdin.append("yes\n")
    response = prompt(question, validator=validator)
    out, _ = capsys.readouterr()
    print(out)
    assert response is True
    assert out == "{0} {1}\n{0} ".format(question, error)


def test_prompt_bool(stdin, capsys):
    question = "Are you sure?"
    stdin.append("yes\n")
    response = prompt_bool(question)
    stdout, _ = capsys.readouterr()
    assert response is True
    assert stdout == "{} [y/N] ".format(question)


def test_prompt_bool_false(stdin, capsys):
    question = "Are you sure?"
    stdin.append("n\n")
    response = prompt_bool(question)
    stdout, _ = capsys.readouterr()
    assert response is False
    assert stdout == "{} [y/N] ".format(question)


def test_prompt_bool_default_true(stdin, capsys):
    question = "Are you sure?"
    stdin.append("\n")
    response = prompt_bool(question, default=True)
    stdout, _ = capsys.readouterr()
    assert response is True
    assert stdout == "{} [Y/n] ".format(question)


def test_prompt_bool_default_false(stdin, capsys):
    question = "Are you sure?"
    stdin.append("\n")
    response = prompt_bool(question, default=False)
    stdout, _ = capsys.readouterr()
    assert response is False
    assert stdout == "{} [y/N] ".format(question)


def test_prompt_bool_no_default(stdin, capsys):
    question = "Are you sure?"
    stdin.append("\ny\n")
    prompt_bool(question, default=None)
    stdout, _ = capsys.readouterr()
    assert '{} [y/n] '.format(question) in stdout
    assert 'Please answer "y" or "n"' in stdout


def test_prompt_bool_invalid(stdin, capsys):
    question = "Are you sure?"
    stdin.append("ARRRR\n")
    # Not ValueError because of capsys
    with pytest.raises(Exception):
        prompt_bool(question)

from os.path import join

import pytest

from .. import copier

from .helpers import read_content


@pytest.mark.parametrize('template', [
    'tests/demo_yaml',
    'tests/demo_json',
    'tests/demo_json_old',
])
def test_read_user_data(dst, template):
    copier.copy(template, dst, force=True)

    gen_file = join(dst, 'user_data.txt')
    result = read_content(gen_file)
    print(result)
    expected = read_content('tests/user_data.ref.txt')
    assert result == expected

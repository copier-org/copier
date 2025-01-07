import warnings

import pytest

import copier
from copier.errors import MultipleYieldTagsError, YieldTagInFileError
from tests.helpers import build_file_tree


def test_folder_loop(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "",
            src
            / "folder_loop"
            / "{% yield item from strings %}{{ item }}{% endyield %}"
            / "{{ item }}.txt.jinja": "Hello {{ item }}",
        }
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        copier.run_copy(
            str(src),
            dst,
            data={
                "strings": ["a", "b", "c"],
            },
            defaults=True,
            overwrite=True,
        )

        expected_files = [dst / f"folder_loop/{i}/{i}.txt" for i in ["a", "b", "c"]]

        for f in expected_files:
            assert f.exists()
            assert f.read_text() == f"Hello {f.parent.name}"

        all_files = [p for p in dst.rglob("*") if p.is_file()]
        unexpected_files = set(all_files) - set(expected_files)

        assert not unexpected_files, f"Unexpected files found: {unexpected_files}"


def test_nested_folder_loop(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "",
            src
            / "nested_folder_loop"
            / "{% yield string_item from strings %}{{ string_item }}{% endyield %}"
            / "{% yield integer_item from integers %}{{ integer_item }}{% endyield %}"
            / "{{ string_item }}_{{ integer_item }}.txt.jinja": "Hello {{ string_item }} {{ integer_item }}",
        }
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        copier.run_copy(
            str(src),
            dst,
            data={
                "strings": ["a", "b"],
                "integers": [1, 2, 3],
            },
            defaults=True,
            overwrite=True,
        )

        expected_files = [
            dst / f"nested_folder_loop/{s}/{i}/{s}_{i}.txt"
            for s in ["a", "b"]
            for i in [1, 2, 3]
        ]

        for f in expected_files:
            assert f.exists()
            assert f.read_text() == f"Hello {f.parent.parent.name} {f.parent.name}"

        all_files = [p for p in dst.rglob("*") if p.is_file()]
        unexpected_files = set(all_files) - set(expected_files)

        assert not unexpected_files, f"Unexpected files found: {unexpected_files}"


def test_file_loop(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "",
            src
            / "file_loop"
            / "{% yield string_item from strings %}{{ string_item }}{% endyield %}.jinja": "Hello {{ string_item }}",
        }
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        copier.run_copy(
            str(src),
            dst,
            data={
                "strings": [
                    "a.txt",
                    "b.txt",
                    "c.txt",
                    "",
                ],  # if rendred as '.jinja', it will not be created
            },
            defaults=True,
            overwrite=True,
        )

        expected_files = [dst / f"file_loop/{i}.txt" for i in ["a", "b", "c"]]
        for f in expected_files:
            assert f.exists()
            assert f.read_text() == f"Hello {f.stem}.txt"

        all_files = [p for p in dst.rglob("*") if p.is_file()]
        unexpected_files = set(all_files) - set(expected_files)

        assert not unexpected_files, f"Unexpected files found: {unexpected_files}"


def test_folder_loop_dict_items(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "",
            src
            / "folder_loop_dict_items"
            / "{% yield dict_item from dicts %}{{ dict_item.folder_name }}{% endyield %}"
            / "{{ dict_item.file_name }}.txt.jinja": "Hello {{ '-'.join(dict_item.content) }}",
        }
    )

    dicts = [
        {
            "folder_name": "folder_a",
            "file_name": "file_a",
            "content": ["folder_a", "file_a"],
        },
        {
            "folder_name": "folder_b",
            "file_name": "file_b",
            "content": ["folder_b", "file_b"],
        },
        {
            "folder_name": "folder_c",
            "file_name": "file_c",
            "content": ["folder_c", "file_c"],
        },
    ]

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        copier.run_copy(
            str(src),
            dst,
            data={"dicts": dicts},
            defaults=True,
            overwrite=True,
        )

        expected_files = [
            dst / f"folder_loop_dict_items/{d['folder_name']}/{d['file_name']}.txt"
            for d in [
                {"folder_name": "folder_a", "file_name": "file_a"},
                {"folder_name": "folder_b", "file_name": "file_b"},
                {"folder_name": "folder_c", "file_name": "file_c"},
            ]
        ]

        for f in expected_files:
            assert f.exists()
            assert f.read_text() == f"Hello {'-'.join([f.parts[-2], f.stem])}"

        all_files = [p for p in dst.rglob("*") if p.is_file()]
        unexpected_files = set(all_files) - set(expected_files)

        assert not unexpected_files, f"Unexpected files found: {unexpected_files}"


def test_raise_yield_tag_in_file(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "",
            src
            / "file.txt.jinja": "{% yield item from strings %}{{ item }}{% endyield %}",
        }
    )

    with pytest.raises(YieldTagInFileError, match="file.txt.jinja"):
        copier.run_copy(
            str(src),
            dst,
            data={
                "strings": ["a", "b", "c"],
            },
            defaults=True,
            overwrite=True,
        )


def test_raise_multiple_yield_tags(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    # multiple yield tags, not nested
    file_name = "{% yield item1 from strings %}{{ item1 }}{% endyield %}{% yield item2 from strings %}{{ item2 }}{% endyield %}"

    build_file_tree(
        {
            src / "copier.yml": "",
            src / file_name: "",
        }
    )

    with pytest.raises(MultipleYieldTagsError, match="item"):
        copier.run_copy(
            str(src),
            dst,
            data={
                "strings": ["a", "b", "c"],
            },
            defaults=True,
            overwrite=True,
        )

    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    # multiple yield tags, nested
    file_name = "{% yield item1 from strings %}{% yield item2 from strings %}{{ item1 }}{{ item2 }}{% endyield %}{% endyield %}"

    build_file_tree(
        {
            src / "copier.yml": "",
            src / file_name: "",
        }
    )

    with pytest.raises(MultipleYieldTagsError, match="item"):
        copier.run_copy(
            str(src),
            dst,
            data={
                "strings": ["a", "b", "c"],
            },
            defaults=True,
            overwrite=True,
        )

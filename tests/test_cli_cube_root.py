"""Tests for cube-root solver CLI selection and validation."""

import pytest

from diophantine_search.__main__ import main
from diophantine_search.families.three_cubes import SearchInstance
from diophantine_search.families.three_cubes_cube_root import cube_root_search


def test_cube_root_cli_output(capsys):
    expected_count = cube_root_search(SearchInstance(3, 5)).triples_checked
    assert main(
        [
            "three-cubes",
            "--k",
            "3",
            "--bound",
            "5",
            "--solver",
            "cube-root",
        ]
    ) == 0
    assert capsys.readouterr().out.splitlines() == [
        "-5 4 4",
        "1 1 1",
        f"# k=3 bound=5 solutions=2 triples_checked={expected_count}",
    ]


def test_cube_root_cli_custom_modulus(capsys):
    expected_count = cube_root_search(SearchInstance(3, 5), 63).triples_checked
    assert main(
        [
            "three-cubes",
            "--k",
            "3",
            "--bound",
            "5",
            "--solver",
            "cube-root",
            "--modulus",
            "63",
        ]
    ) == 0
    assert capsys.readouterr().out.splitlines()[-1] == (
        f"# k=3 bound=5 solutions=2 triples_checked={expected_count}"
    )


@pytest.mark.parametrize("modulus", [43_010, 0])
def test_cube_root_cli_rejects_invalid_modulus(modulus, capsys):
    with pytest.raises(SystemExit) as error:
        main(
            [
                "three-cubes",
                "--k",
                "3",
                "--bound",
                "5",
                "--solver",
                "cube-root",
                "--modulus",
                str(modulus),
            ]
        )
    assert error.value.code == 2
    assert "error:" in capsys.readouterr().err

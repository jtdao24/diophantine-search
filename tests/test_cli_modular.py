"""Tests for modular-solver CLI selection and validation."""

import pytest

from diophantine_search.__main__ import main
from diophantine_search.families.three_cubes import SearchInstance
from diophantine_search.families.three_cubes_modular import modular_search


def test_modular_cli_output(capsys):
    expected_count = modular_search(SearchInstance(3, 5)).triples_checked
    assert main(
        ["three-cubes", "--k", "3", "--bound", "5", "--solver", "modular"]
    ) == 0
    assert capsys.readouterr().out.splitlines() == [
        "-5 4 4",
        "1 1 1",
        f"# k=3 bound=5 solutions=2 triples_checked={expected_count}",
    ]
    assert expected_count < 286


def test_modular_cli_custom_modulus(capsys):
    expected_count = modular_search(SearchInstance(3, 5), 63).triples_checked
    assert main(
        [
            "three-cubes",
            "--k",
            "3",
            "--bound",
            "5",
            "--solver",
            "modular",
            "--modulus",
            "63",
        ]
    ) == 0
    assert capsys.readouterr().out.splitlines()[-1] == (
        f"# k=3 bound=5 solutions=2 triples_checked={expected_count}"
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["three-cubes", "--k", "3", "--bound", "5", "--modulus", "63"],
        [
            "three-cubes",
            "--k",
            "3",
            "--bound",
            "5",
            "--solver",
            "modular",
            "--modulus",
            "0",
        ],
        [
            "three-cubes",
            "--k",
            "3",
            "--bound",
            "5",
            "--solver",
            "modular",
            "--modulus",
            "100001",
        ],
    ],
)
def test_modular_cli_errors(argv, capsys):
    with pytest.raises(SystemExit) as error:
        main(argv)
    assert error.value.code == 2
    assert "error:" in capsys.readouterr().err

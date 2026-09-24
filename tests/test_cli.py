"""Tests for the command-line interface."""

import pytest

from diophantine_search.__main__ import main


def test_three_cubes_output(capsys):
    assert main(["three-cubes", "--k", "3", "--bound", "5"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "-5 4 4",
        "1 1 1",
        "# k=3 bound=5 solutions=2 triples_checked=286",
    ]


def test_negative_k(capsys):
    assert main(["three-cubes", "--k", "-3", "--bound", "5"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "-4 -4 5",
        "-1 -1 -1",
        "# k=-3 bound=5 solutions=2 triples_checked=286",
    ]


def test_trivial_suffix(capsys):
    assert main(["three-cubes", "--k", "8", "--bound", "4"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "-4 2 4 trivial",
        "-3 2 3 trivial",
        "-2 2 2 trivial",
        "-1 1 2 trivial",
        "0 0 2 trivial",
        "# k=8 bound=4 solutions=5 triples_checked=165",
    ]


@pytest.mark.parametrize(
    "argv",
    [
        ["three-cubes", "--k", "1", "--bound", "-1"],
        [],
    ],
)
def test_argparse_errors(argv, capsys):
    with pytest.raises(SystemExit) as error:
        main(argv)
    assert error.value.code == 2
    assert "error:" in capsys.readouterr().err

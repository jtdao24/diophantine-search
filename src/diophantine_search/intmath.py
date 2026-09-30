"""Exact integer-only mathematical helpers."""


def _require_int(n: int) -> None:
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n must be an int")


def icbrt_floor(n: int) -> int:
    """Return the largest integer r such that r³ is at most n."""

    _require_int(n)
    if n < 0:
        return -icbrt_ceil(-n)
    if n < 2:
        return n

    x = 1 << ((n.bit_length() + 2) // 3)
    while True:
        y = (2 * x + n // (x * x)) // 3
        if y >= x:
            break
        x = y

    while (x + 1) ** 3 <= n:
        x += 1
    while x**3 > n:
        x -= 1
    return x


def icbrt_ceil(n: int) -> int:
    """Return the smallest integer r such that r³ is at least n."""

    _require_int(n)
    root = icbrt_floor(n)
    return root if root**3 == n else root + 1


def exact_cube_root(n: int) -> int | None:
    """Return the integer cube root of n when it exists exactly."""

    _require_int(n)
    root = icbrt_floor(n)
    return root if root**3 == n else None

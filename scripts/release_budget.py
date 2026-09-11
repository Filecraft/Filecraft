"""Hard decimal-byte budgets for the distributable, not the Swift toolchain."""
LIMITS = {'binary': 2_000_000, 'app': 3_000_000, 'archive': 1_500_000}


def validate_sizes(*, binary: int, app: int, archive: int) -> None:
    for name, size in dict(binary=binary, app=app, archive=archive).items():
        if not 0 < size < LIMITS[name]:
            raise ValueError(f'{name}: {size:,} bytes; must be positive and below {LIMITS[name]:,}')

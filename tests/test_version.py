import re

from app.version import __version__

# Core SemVer: MAJOR.MINOR.PATCH, optional pre-release and build metadata.
_SEMVER_PATTERN = re.compile(
    r"^(?P<core>\d+\.\d+\.\d+)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def test_version_matches_semver() -> None:
    assert _SEMVER_PATTERN.match(__version__), f"Invalid SemVer string: {__version__!r}"

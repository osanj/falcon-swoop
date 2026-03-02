import nox

PY_VERSIONS = ["3.10", "3.12"]
# PY_VERSIONS = ["3.10", "3.11", "3.12", "3.13"]


# @nox.session(python=PY_VERSIONS)
# def install(session: nox.Session):
#     session.install("-e", ".[dev]")


@nox.session(python=PY_VERSIONS)
def matrix(session: nox.Session):
    session.install("-e", ".[dev]")

    session.run("ruff", "check")
    session.run("ruff", "format", "--check")
    session.run("mypy")

    session.run("pytest", "-v")

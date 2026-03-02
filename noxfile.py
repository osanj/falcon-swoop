import nox

PY_VERSIONS = ["3.10", "3.12"]  # ["3.10", "3.11", "3.12", "3.13"]
PYDANTIC_NEWEST = "2"
PYDANTIC_VERSIONS = [PYDANTIC_NEWEST, "2.12", "2.11", "2.10", "2.9", "2.6", "2.4", "2.0"]


@nox.session(python=PY_VERSIONS)
@nox.parametrize("pydantic", PYDANTIC_VERSIONS)
def matrix(session: nox.Session, pydantic: str):
    session.install("-e", ".[dev]")

    verbose = "verbose" in session.posargs

    # run lint only on main version
    if pydantic == PYDANTIC_NEWEST:
        session.run("ruff", "check")
        session.run("ruff", "format", "--check")
        session.run("mypy")

    else:
        session.install(f"pydantic=={pydantic}")

    pytest_args = ["pytest"]
    if verbose:
        pytest_args.append("v")
    session.run(*pytest_args)

from urllib.parse import quote

from rich.console import Console
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy_utils import create_database, database_exists, drop_database

from macrostrat.utils import ApplicationError, get_logger

console = Console()

log = get_logger(__name__)


def _docker_local_run_args(postgres_container: str = "postgres:15"):
    return [
        "docker",
        "run",
        "-i",
        "--network",
        "host",
        "--attach",
        "stdin",
        "--attach",
        "stdout",
        "--attach",
        "stderr",
        "--log-driver",
        "none",
        "--rm",
        postgres_container,
    ]


def _create_database_if_not_exists(
    _url: URL, *, create=False, allow_exists=True, overwrite=False
):
    database = _url.database
    if overwrite:
        create = True
    db_exists = database_exists(_url)
    if db_exists:
        msg = f"Database [bold underline]{database}[/] already exists"
        if overwrite:
            console.print(f"{msg}, overwriting")
            drop_database(_url)
            db_exists = False
        elif not allow_exists:
            raise ApplicationError(msg, details="Use `--overwrite` to overwrite")
        else:
            console.print(msg)

    if create and not db_exists:
        console.print(f"Creating database [bold cyan]{database}[/]")
        create_database(_url)

    if not db_exists and not create:
        raise ApplicationError(
            f"Database [bold cyan]{database}[/] does not exist. ",
            "Use `--create` to create it.",
        )


def _create_command(
    engine: Engine,
    *command,
    args=None | list[str],
    prefix=None | list[str],
    container="postgres:16",
):
    if args is None:
        args = []

    command_prefix = prefix or _docker_local_run_args(container)
    _cmd = [*command_prefix, *command, str(engine.url), *args]

    log.info(" ".join(_cmd))

    # Replace asterisks with the real password (if any). This is kind of backwards
    # but it works.
    if "***" in str(engine.url) and engine.url.password is not None:
        _cmd = [
            *command_prefix,
            *command,
            raw_database_url(engine.url),
            *args,
        ]

    return _cmd


def raw_database_url(url: URL):
    """Replace the password asterisks with the actual password, in order to pass to other commands."""
    _url = str(url)
    if "***" not in _url or url.password is None:
        return _url
    return _url.replace("***", quote(url.password, safe=""))

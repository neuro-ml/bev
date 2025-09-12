from functools import wraps

import typer

from ..exceptions import BevError


_app = typer.Typer()


class CliError(Exception):
    pass


def cli_error(exc, msg):
    class Exc(CliError, exc):
        pass

    return Exc(msg)


def command(application):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)

            except BevError as e:
                print(type(e).__name__, e)
                raise typer.Exit(code=255) from e

            except CliError as e:
                print(e)
                raise typer.Exit(code=255) from e

            except KeyboardInterrupt as e:
                raise typer.Abort() from e

            except BaseException:
                print('An exception occurred. Please leave an issue at https://github.com/neuro-ml/bev/issues')
                raise

        application.command()(wrapper)
        return func

    return decorator


app_command = command(_app)

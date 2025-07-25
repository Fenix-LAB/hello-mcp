import os
import click
import uvicorn

from config.config import config


@click.command()
@click.option(
    "--env",
    type=click.Choice(["local", "dev", "prod"], case_sensitive=False),
    default="local",
)
@click.option(
    "--debug",
    type=click.BOOL,
    is_flag=True,
    default=False,
)
def main(env: str, debug: bool):
    os.environ["ENV"] = env
    os.environ["DEBUG"] = str(debug)
    uvicorn.run(
        app="app.server:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=True if config.ENV != "production" else False,
        workers=1,
    )


if __name__ == "__main__":
    main()

# Run the following command to start the FastAPI server:
# python main.py
# Run the following command to start the FastAPI server in development mode:
# python main.py --env dev --debug
# Run the following command to start the FastAPI server in production mode:
# python main.py --env prod
# Run the following command to start the FastAPI server in local mode:
# python main.py --env local

# Defaul mode is local
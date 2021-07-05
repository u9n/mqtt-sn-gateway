import asyncio
import uvloop
import logging
import click
from config import Config
import async_server


LOG = logging.getLogger(__name__)


async def async_main(config: Config):

    gw = async_server.MQTTSNGatewayServer(host=config.HOST, port=config.PORT)
    try:
        await gw.run()

    except (asyncio.CancelledError, KeyboardInterrupt):
        LOG.info("MQTT-SN Gateway cancelled")
        await gw.teardown()
        LOG.info("MQTT-SN Gateway closed down")


@click.command()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--env-file", default=None, help="Path to .env file")
@click.option("--no-env-files", is_flag=True, help="Discard all use of .env files.")
def main(debug, env_file, no_env_files):
    """
    Will assume there is a .env file in the root of the package. This is for simple development.
    To use .env files as in production use the --env-file arg to specify path.
    To make force the application to discard all .env files use the --no-env-files flag.

    """
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        uvloop.install()
        config = Config(env_file, no_env_files=no_env_files)
        asyncio.run(async_main(config), debug=True)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":

    main()

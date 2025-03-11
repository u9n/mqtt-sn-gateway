import logging

import structlog
import click
from mqtt_sn_gateway.config import Config
from mqtt_sn_gateway.server import ThreadingUdpServer, MqttSnRequestHandler

LOG = structlog.get_logger()


@click.command()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--env-file", default=None, help="Path to .env file")
@click.option("--no-env-files", is_flag=True, help="Discard all use of .env files.")
@click.option("--json-logs", is_flag=True, help="Outputs logs in JSON-format")
def main(debug, env_file, no_env_files: bool, json_logs: bool):
    """
    Will assume there is a .env file in the root of the package. This is for simple development.
    To use .env files as in production use the --env-file arg to specify path.
    To make force the application to discard all .env files use the --no-env-files flag.

    """

    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    structlog_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),

    ]
    if json_logs:
        structlog_processors.append(structlog.processors.JSONRenderer())
    else:
        structlog_processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=structlog_processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False
    )

    try:
        config = Config(env_file, no_env_files=no_env_files)
        mqtt_sn_server = ThreadingUdpServer((config.HOST, config.PORT), MqttSnRequestHandler, config=config)
        with mqtt_sn_server as server:
            LOG.info("Starting MQTT-SN server", host=config.HOST, port=config.PORT)
            server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("Stopping MQTT-SN server")


if __name__ == "__main__":
    main(auto_envvar_prefix="MQTTSN")

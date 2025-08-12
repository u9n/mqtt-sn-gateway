import logging

import structlog
import click
from mqtt_sn_gateway.config import Config
from mqtt_sn_gateway.server import ThreadingUdpServer, MqttSnRequestHandler
import sentry_sdk
from structlog_sentry import SentryProcessor

LOG = structlog.get_logger()


@click.command()
@click.option("--debug", is_flag=True, help="Enable debug logging", envvar="MQTTSN_DEBUG")
@click.option("--env-file", default=None, help="Path to .env file", envvar="MQTTSN_ENV_FILE")
@click.option("--no-env-files", is_flag=True, help="Discard all use of .env files.", envvar="MQTTSN_NO_ENV_FILES")
@click.option("--json-logs", is_flag=True, help="Outputs logs in JSON-format", envvar="MQTTSN_JSON_LOGS")
def main(debug, env_file, no_env_files: bool, json_logs: bool):
    """
    Will assume there is a .env file in the root of the package. This is for simple development.
    To use .env files as in production use the --env-file arg to specify path.
    To make force the application to discard all .env files use the --no-env-files flag.

    """
    config = Config(env_file, no_env_files=no_env_files)
    print(config)
    if config.SENTRY_DSN:
        sentry_sdk.init(
            dsn=config.SENTRY_DSN,
            # Add request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
        )
        LOG.info("Initiated Sentry SDK for error tracking")

    if debug:
        LOG.info("Debug is enabled")
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    structlog_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        SentryProcessor(event_level=logging.CRITICAL),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),

    ]
    if json_logs:
        # Have to disable the
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
        mqtt_sn_server = ThreadingUdpServer((config.HOST, config.PORT), MqttSnRequestHandler, config=config)
        with mqtt_sn_server as server:
            LOG.info("Starting MQTT-SN server", host=config.HOST, port=config.PORT)
            server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("Stopping MQTT-SN server")



if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from weather_daemon.config import WeatherConfig
from weather_daemon.daemon import WeatherDaemon
from weather_daemon.healthcheck import HealthCheckServer
from weather_daemon.logging_config import setup_logging as configure_logging


def cmd_run(args: argparse.Namespace) -> int:
    """Run the weather daemon."""
    # Load configuration
    try:
        config = WeatherConfig.from_env(args.config)
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Setup logging
    json_format = getattr(config, 'log_format', 'text') == 'json'
    configure_logging(config.log_level, json_format=json_format)
    logger = logging.getLogger(__name__)

    # Create daemon
    daemon = WeatherDaemon(
        api_key=config.api_key,
        output_dir=config.output_dir,
        latitude=config.latitude,
        longitude=config.longitude,
        location_name=config.location_name,
        poll_interval=config.poll_interval,
        timeout=config.timeout,
        api_base_url=config.api_base_url,
        current_conditions_endpoint=config.current_conditions_endpoint,
        hourly_forecast_endpoint=config.hourly_forecast_endpoint,
        daily_forecast_endpoint=config.daily_forecast_endpoint,
    )

    # Start health check server if enabled
    health_server = None
    if config.health_check_enabled:
        health_server = HealthCheckServer(
            daemon,
            host=config.health_check_host,
            port=config.health_check_port
        )
        health_server.start()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler(sig: int, frame: object) -> None:
        logger.info(f"Received signal {sig}, shutting down...")
        daemon.stop()
        if health_server:
            health_server.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run daemon
    try:
        loop.run_until_complete(daemon.run())
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        if health_server:
            health_server.stop()
        loop.close()


def cmd_test(args: argparse.Namespace) -> int:
    """Test configuration and fetch weather once."""
    # Load configuration
    try:
        config = WeatherConfig.from_env(args.config)
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Setup logging
    configure_logging("INFO", json_format=False)
    logger = logging.getLogger(__name__)

    # Create daemon and run once
    daemon = WeatherDaemon(
        api_key=config.api_key,
        output_dir=config.output_dir,
        latitude=config.latitude,
        longitude=config.longitude,
        location_name=config.location_name,
        poll_interval=config.poll_interval,
        timeout=config.timeout,
        api_base_url=config.api_base_url,
        current_conditions_endpoint=config.current_conditions_endpoint,
        hourly_forecast_endpoint=config.hourly_forecast_endpoint,
        daily_forecast_endpoint=config.daily_forecast_endpoint,
    )

    async def test_fetch() -> None:
        await daemon._poll_once()

    try:
        asyncio.run(test_fetch())
        logger.info("Test fetch completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='weather-daemon',
        description='Weather daemon that generates static JSON from Google Maps Weather API'
    )
    parser.add_argument('--version', action='store_true', help='Show version')

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # run command
    run_parser = subparsers.add_parser('run', help='Run the weather daemon')
    run_parser.add_argument(
        '--config',
        type=Path,
        help='Path to .env config file (default: .env in current directory)'
    )

    # test command
    test_parser = subparsers.add_parser('test', help='Test configuration and fetch weather once')
    test_parser.add_argument(
        '--config',
        type=Path,
        help='Path to .env config file (default: .env in current directory)'
    )

    args = parser.parse_args(argv)

    if args.version:
        from weather_daemon import __version__
        print(__version__)
        return 0

    if args.command == 'run':
        return cmd_run(args)
    elif args.command == 'test':
        return cmd_test(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    raise SystemExit(main())

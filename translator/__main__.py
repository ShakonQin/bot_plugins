"""独立运行 Translator 服务

用法:
    python -m plugins.translator [--config path/to/config.yaml]
"""

import argparse
import asyncio
import logging
import signal

from .main import TranslatorService


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def async_main(config_path: str | None) -> None:
    service = TranslatorService(config_path=config_path)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.get_event_loop().stop())

    await service.run_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="中英互译服务")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="配置文件路径（默认使用插件目录下的 config.yaml）",
    )
    args = parser.parse_args()

    setup_logging()
    asyncio.run(async_main(args.config))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""BoChat 插件启动器

同时或单独启动 github_subscriber 和 translator 服务。

用法:
    # 启动所有插件
    python plugins/run.py

    # 只启动 github_subscriber
    python plugins/run.py --only github_subscriber

    # 只启动 translator
    python plugins/run.py --only translator

    # 指定配置文件
    python plugins/run.py --github-config plugins/github_subscriber/config.yaml \
                           --translator-config plugins/translator/config.yaml
"""

import argparse
import asyncio
import logging
import signal

from plugins.github_subscriber.main import GitHubSubscriberService
from plugins.translator.main import TranslatorService

LOG = logging.getLogger("PluginRunner")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run_all(
    github_config: str | None,
    translator_config: str | None,
    only: str | None,
) -> None:
    services = []

    if only is None or only == "github_subscriber":
        gh_service = GitHubSubscriberService(config_path=github_config)
        services.append(("GitHubSubscriber", gh_service))

    if only is None or only == "translator":
        trans_service = TranslatorService(config_path=translator_config)
        services.append(("Translator", trans_service))

    if not services:
        LOG.error("没有要启动的服务")
        return

    # 启动所有服务
    tasks = []
    for name, service in services:
        LOG.info("正在启动 %s ...", name)
        task = asyncio.create_task(service.run_forever())
        tasks.append((name, task))

    # 等待所有服务结束（或收到取消信号）
    try:
        await asyncio.gather(*[t for _, t in tasks])
    except asyncio.CancelledError:
        LOG.info("收到停止信号，正在关闭服务...")
        for name, service in services:
            await service.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="BoChat 插件启动器")
    parser.add_argument(
        "--only",
        type=str,
        choices=["github_subscriber", "translator"],
        default=None,
        help="只启动指定插件（默认启动全部）",
    )
    parser.add_argument(
        "--github-config",
        type=str,
        default=None,
        help="github_subscriber 配置文件路径",
    )
    parser.add_argument(
        "--translator-config",
        type=str,
        default=None,
        help="translator 配置文件路径",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )
    args = parser.parse_args()

    setup_logging(args.log_level)

    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: loop.stop())

    try:
        loop.run_until_complete(
            run_all(args.github_config, args.translator_config, args.only)
        )
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()

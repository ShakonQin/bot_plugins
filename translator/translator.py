"""翻译 API 客户端

支持 MyMemory（免费）和百度翻译两种后端。
"""

from __future__ import annotations

import hashlib
import logging
import random
from typing import Any

import httpx

LOG = logging.getLogger("Translator")

MYMEMORY_URL = "https://api.mymemory.translated.net/get"
BAIDU_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"

LANG_MAP = {
    "c2e": ("zh-CN", "en"),
    "e2c": ("en", "zh-CN"),
}

BAIDU_LANG_MAP = {
    "c2e": ("zh", "en"),
    "e2c": ("en", "zh"),
}


class TranslateError(Exception):
    pass


class TranslateClient:
    def __init__(self, provider: str = "mymemory", **kwargs: Any) -> None:
        self._provider = provider
        self._opts = kwargs
        self._http = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        await self._http.aclose()

    async def translate(self, text: str, mode: str) -> str:
        if self._provider == "baidu":
            return await self._baidu(text, mode)
        return await self._mymemory(text, mode)

    async def _mymemory(self, text: str, mode: str) -> str:
        src, tgt = LANG_MAP[mode]
        params: dict[str, str] = {
            "q": text,
            "langpair": f"{src}|{tgt}",
        }
        email = self._opts.get("email")
        if email:
            params["de"] = email

        resp = await self._http.get(MYMEMORY_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        if data.get("responseStatus") != 200:
            raise TranslateError(data.get("responseDetails", "翻译请求失败"))

        return data["responseData"]["translatedText"]

    async def _baidu(self, text: str, mode: str) -> str:
        app_id = self._opts.get("app_id", "")
        secret_key = self._opts.get("secret_key", "")
        if not app_id or not secret_key:
            raise TranslateError("百度翻译未配置 app_id / secret_key")

        src, tgt = BAIDU_LANG_MAP[mode]
        salt = str(random.randint(10000, 99999))
        sign_str = f"{app_id}{text}{salt}{secret_key}"
        sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

        params = {
            "q": text,
            "from": src,
            "to": tgt,
            "appid": app_id,
            "salt": salt,
            "sign": sign,
        }

        resp = await self._http.post(BAIDU_URL, data=params)
        resp.raise_for_status()
        data = resp.json()

        if "error_code" in data:
            raise TranslateError(
                f"百度翻译错误 {data['error_code']}: {data.get('error_msg', '')}"
            )

        results = data.get("trans_result", [])
        if not results:
            raise TranslateError("百度翻译返回空结果")

        return "\n".join(item["dst"] for item in results)

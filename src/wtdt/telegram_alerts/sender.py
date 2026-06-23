import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_MESSAGE_LIMIT = 4096


@dataclass(frozen=True)
class TelegramSender:
    token: str
    chat_id: str
    dry_run: bool = True
    timeout_s: float = 15.0

    def send(self, text: str) -> bool:
        if self.dry_run or not self.token or not self.chat_id:
            log.info("[dry-run telegram] chat=%s text=%r", self.chat_id, text)
            print(f"\n[Telegram -> {self.chat_id}]\n{text}\n")
            return True

        ok = True
        for chunk in chunks(text):
            if not self._post_message(chunk):
                ok = False
        return ok

    def _post_message(self, text: str) -> bool:
        url = f"{TELEGRAM_API}/bot{self.token}/sendMessage"
        data = json.dumps({"chat_id": self.chat_id, "text": text}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                if response.status >= 300:
                    log.error("telegram send failed: HTTP %s", response.status)
                    return False
        except urllib.error.HTTPError as exc:
            body = exc.read(300).decode("utf-8", errors="replace")
            log.error("telegram send failed: HTTP %s %s", exc.code, body)
            return False
        except urllib.error.URLError as exc:
            log.error("telegram send failed: %s", exc.reason)
            return False
        return True


def chunks(text: str) -> list[str]:
    return [
        text[index : index + TELEGRAM_MESSAGE_LIMIT]
        for index in range(0, len(text), TELEGRAM_MESSAGE_LIMIT)
    ] or [""]


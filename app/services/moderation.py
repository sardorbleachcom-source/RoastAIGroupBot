import re
import time
from collections import defaultdict, deque

_recent = defaultdict(deque)
_last = {}

URL_RE = re.compile(
    r"(https?://|www\.|t\.me/|telegram\.me/)", re.IGNORECASE
)

def check_message(chat_id, user_id, text):
    now = time.monotonic()
    key = (chat_id, user_id)
    queue = _recent[key]

    while queue and now - queue[0] > 10:
        queue.popleft()
    queue.append(now)

    if len(queue) > 7:
        return "flood"

    normalized = " ".join((text or "").lower().split())
    previous = _last.get(key)

    if normalized and previous:
        previous_text, previous_time = previous
        if normalized == previous_text and now - previous_time <= 10:
            _last[key] = (normalized, now)
            return "repeat"

    _last[key] = (normalized, now)

    if URL_RE.search(text or ""):
        return "link"

    return None

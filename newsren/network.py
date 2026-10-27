"""Bounded response bodies with elapsed-time checks between reads."""

import time


def read_bounded(response, limit: int, deadline: float, clock=time.monotonic) -> bytes:
    chunks, total = [], 0
    read = getattr(response, "read1", None) or response.read
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError("Response read deadline exceeded")
        # HTTPResponse exposes its transport through the buffered reader. Tighten the
        # next socket wait where available; elapsed checks also handle active streams.
        try:
            sock = response.fp.raw._sock
            current = sock.gettimeout()
            sock.settimeout(min(remaining, current) if current is not None else remaining)
        except AttributeError:
            pass
        chunk = read(min(65536, limit - total + 1))
        if clock() >= deadline:
            raise TimeoutError("Response read deadline exceeded")
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > limit:
            raise ValueError("Response body exceeded the byte limit")
        chunks.append(chunk)

import io
import unittest

from newsren import network


class NetworkTests(unittest.TestCase):
    def reader(self, response, **kwargs):
        self.assertTrue(hasattr(network, "read_bounded"))
        return network.read_bounded(response, **kwargs)

    def test_response_body_cap_rejects_oversized_stream(self):
        with self.assertRaises(ValueError):
            self.reader(io.BytesIO(b"a" * 100), limit=50, deadline=10, clock=lambda: 0)

    def test_drip_feed_is_stopped_by_elapsed_read_deadline(self):
        clock = [0.0]
        class Drip:
            def read1(self, size):
                clock[0] += 0.4
                return b"a"
        with self.assertRaises(TimeoutError):
            self.reader(Drip(), limit=100, deadline=1, clock=lambda: clock[0])
        self.assertLess(clock[0], 1.5)

    def test_complete_small_response_is_unchanged(self):
        self.assertEqual(self.reader(io.BytesIO(b"a valid response"), limit=100, deadline=10, clock=lambda: 0), b"a valid response")

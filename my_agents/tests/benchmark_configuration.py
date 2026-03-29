from __future__ import annotations

import timeit
import unittest

from my_agents.configuration import normalize_profile_key

TEST_CASES = [
    "D2C Brands",
    "healthcare",
    "deep-tech",
    "marketplace",
    "cyber security",
    "Health / Wellness",
    "Fin & Tech",
    "AI   Startup   ",
    "foo__bar--baz//qux",
    None,
]

class ConfigurationBenchmarks(unittest.TestCase):
    def test_normalize_profile_key_benchmark(self):
        def run_bench():
            for case in TEST_CASES:
                normalize_profile_key(case)

        # Warmup
        run_bench()

        iterations = 100000
        time_taken = timeit.timeit(run_bench, number=iterations)
        print(f"\n--- BENCHMARK RESULTS ---")
        print(f"normalize_profile_key: {time_taken:.4f} seconds for {iterations} iterations of {len(TEST_CASES)} cases.")
        print(f"Average time per call: {(time_taken / (iterations * len(TEST_CASES))) * 1e6:.4f} μs")
        print(f"-------------------------\n")


if __name__ == "__main__":
    unittest.main()

import time
import random
import tracemalloc

from .bplustree import BPlusTree
from .bruteforce import BruteForceDB


class PerformanceAnalyzer:

    def __init__(self, order=8, seed=42):
        self.order = order
        random.seed(seed)  # reproducibility

    #  helper 

    @staticmethod
    def _time_and_mem(func):
        tracemalloc.start()
        t0 = time.perf_counter()

        try:
            func()
        except Exception as e:
            print("Error during benchmark:", e)
            tracemalloc.stop()
            return 0, 0

        elapsed = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return elapsed, peak

    #  benchmarks 

    def measure_insert(self, keys):
        bpt = BPlusTree(order=self.order)
        bft = BruteForceDB()

        def bpt_ins():
            for k in keys:
                bpt.insert(k, k)

        def bft_ins():
            for k in keys:
                bft.insert(k)

        return {
            "bptree": self._time_and_mem(bpt_ins),
            "brute": self._time_and_mem(bft_ins),
        }

    def measure_search(self, keys):
        bpt = BPlusTree(order=self.order)
        bft = BruteForceDB()

        for k in keys:
            bpt.insert(k, k)
            bft.insert(k)

        search_keys = random.sample(keys, min(len(keys), 200))

        def bpt_srch():
            for k in search_keys:
                bpt.search(k)

        def bft_srch():
            for k in search_keys:
                bft.search(k)

        return {
            "bptree": self._time_and_mem(bpt_srch),
            "brute": self._time_and_mem(bft_srch),
        }

    def measure_delete(self, keys):
        bpt = BPlusTree(order=self.order)
        bft = BruteForceDB()

        for k in keys:
            bpt.insert(k, k)
            bft.insert(k)

        del_keys = random.sample(keys, min(len(keys), 200))

        def bpt_del():
            for k in del_keys:
                bpt.delete(k)

        def bft_del():
            for k in del_keys:
                bft.delete(k)

        return {
            "bptree": self._time_and_mem(bpt_del),
            "brute": self._time_and_mem(bft_del),
        }

    def measure_range(self, keys):
        bpt = BPlusTree(order=self.order)
        bft = BruteForceDB()

        for k in keys:
            bpt.insert(k, k)
            bft.insert(k)

        sorted_keys = sorted(keys)
        mid = len(sorted_keys) // 2
        start = sorted_keys[mid]
        end = sorted_keys[min(mid + 20, len(sorted_keys) - 1)]

        def bpt_rng():
            for _ in range(200):
                bpt.range_query(start, end)

        def bft_rng():
            for _ in range(200):
                bft.range_query(start, end)

        return {
            "bptree": self._time_and_mem(bpt_rng),
            "brute": self._time_and_mem(bft_rng),
        }

    def measure_random(self, keys):
        bpt = BPlusTree(order=self.order)
        bft = BruteForceDB()

        ops = (
            ["insert"] * int(0.4 * len(keys)) +
            ["search"] * int(0.3 * len(keys)) +
            ["delete"] * int(0.3 * len(keys))
        )
        random.shuffle(ops)

        def run_bpt():
            inserted = []
            for i, op in enumerate(ops):
                k = keys[i % len(keys)]
                if op == "insert":
                    bpt.insert(k, k)
                    inserted.append(k)
                elif op == "search":
                    bpt.search(k)
                elif op == "delete" and inserted:
                    bpt.delete(inserted.pop())

        def run_bft():
            inserted = []
            for i, op in enumerate(ops):
                k = keys[i % len(keys)]
                if op == "insert":
                    bft.insert(k)
                    inserted.append(k)
                elif op == "search":
                    bft.search(k)
                elif op == "delete" and inserted:
                    bft.delete(inserted.pop())

        return {
            "bptree": self._time_and_mem(run_bpt),
            "brute": self._time_and_mem(run_bft),
        }

    def measure_memory(self, keys):

        def bpt_mem():
            bpt = BPlusTree(order=self.order)
            for k in keys:
                bpt.insert(k, k)

        def bft_mem():
            bft = BruteForceDB()
            for k in keys:
                bft.insert(k)

        return {
            "bptree": self._time_and_mem(bpt_mem),
            "brute": self._time_and_mem(bft_mem),
        }

    #  full benchmark 

    def run_full_benchmark(self, sizes=None):

        if sizes is None:
            sizes = list(range(100, 5001, 500))

        results = {
            "sizes": sizes,
            "insert": {"bptree": [], "brute": []},
            "search": {"bptree": [], "brute": []},
            "delete": {"bptree": [], "brute": []},
            "range": {"bptree": [], "brute": []},
            "random": {"bptree": [], "brute": []},
            "memory": {"bptree": [], "brute": []},
        }

        for n in sizes:
            print(f"Benchmarking n={n}...")

            keys = random.sample(range(1, 1_000_000), n)

            r = self.measure_insert(keys)
            results["insert"]["bptree"].append(r["bptree"][0])
            results["insert"]["brute"].append(r["brute"][0])

            r = self.measure_search(keys)
            results["search"]["bptree"].append(r["bptree"][0])
            results["search"]["brute"].append(r["brute"][0])

            r = self.measure_delete(keys)
            results["delete"]["bptree"].append(r["bptree"][0])
            results["delete"]["brute"].append(r["brute"][0])

            r = self.measure_range(keys)
            results["range"]["bptree"].append(r["bptree"][0])
            results["range"]["brute"].append(r["brute"][0])

            r = self.measure_random(keys)
            results["random"]["bptree"].append(r["bptree"][0])
            results["random"]["brute"].append(r["brute"][0])

            r = self.measure_memory(keys)
            results["memory"]["bptree"].append(r["bptree"][1])
            results["memory"]["brute"].append(r["brute"][1])

        return results
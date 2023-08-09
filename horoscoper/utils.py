import random


def produce_n_delays(overall_time: int, n: int) -> list[int]:
    delays = [random.random() for _ in range(n)]
    coeff = overall_time / sum(delays)
    return [delay * coeff for delay in delays]

import random

class ArchiveRandomizerBase:
    def __init__(self, seed: str = None, min_chunk_ratio: float = 0.7):
        self.seed = seed
        self.min_chunk_ratio = min_chunk_ratio
        self._original_seed_state = random.getstate() if seed else None
        if seed:
            random.seed(seed)
        pass

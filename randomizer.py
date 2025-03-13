import random
from .archive_parts_randomizer_base import ArchiveRandomizerBase

class ArchivePartsRandomizer(ArchiveRandomizerBase):
    def __init__(self, seed: str = None, min_chunk_ratio: float = 0.7):
        super().__init__(seed, min_chunk_ratio)
        pass

    def _generate_random_extension(self) -> str:
        """Generate a random file extension to help disguise the archive"""
        extensions = ['jpg']  # can be: ['jpg', 'png', 'mp4', 'mov', 'pdf', 'doc']
        return random.choice(extensions)

    def _generate_archive_name(self, base_path: str, index: int, subindex: int = None) -> str:
        """Generate deterministic randomized filename using seed"""
        if not self.seed:
            return base_path
        
        # Save original random state
        original_state = random.getstate()
        
        # Generate name components using seed-based randomization
        random.seed(f"{self.seed}-{index}-{subindex}")
        random_chars = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=4))
        extension = self._generate_random_extension()
        
        # Restore original random state
        random.setstate(original_state)
        
        return f"{self.seed}-{index}-{subindex}-{random_chars}.{extension}"

    def _get_random_chunk_size(self, max_size: int, piece_size: int, chunk_index: int) -> int:
        """Generate random chunk size between min_ratio and max of piece_size"""
        if self.seed:
            chunk_seed = f"{self.seed}-{piece_size}-{chunk_index}"
            random.seed(chunk_seed)
        
        # Calculate minimum size based on piece_size, not remaining size
        min_size = int(piece_size * self.min_chunk_ratio)
        
        # Use beta distribution between min_size and max_size
        ratio = random.betavariate(0.8, 0.8)
        size = min_size + int((max_size - min_size) * ratio)
        
        # Add small jitter while maintaining minimum size
        jitter = random.uniform(1.0, 1.05)  # Only allow upward jitter
        size = int(size * jitter)
        
        # Add small prime offset while ensuring we don't go below min_size
        prime_offset = random.choice([0, 311, 733])  # Only positive offsets
        size = min(max_size, size + prime_offset)
        
        if self.seed:
            random.setstate(self._original_seed_state)
        
        return size
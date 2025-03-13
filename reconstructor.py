import os
import glob
from typing import List
import random
from .archive_parts_randomizer_base import ArchiveRandomizerBase
from ...wrapers.logging import logging
from ...constants import Msg
import rarfile

class ArchivePartsReconstructor(ArchiveRandomizerBase):
    def __init__(self, seed: str = None, min_chunk_ratio: float = 0.7):
        super().__init__(seed, min_chunk_ratio)
        pass

    def _reconstruct_file(self, chunks: List[str], output_path: str, expected_size: int) -> bool:
        """Reconstruct a file from its chunks with precomputed size"""
        logging.info(f"🔵 Starting reconstruction of {output_path}")
        logging.debug(f"Chunks to process: {len(chunks)}")
        
        try:
            total_written = 0
            with open(output_path, 'wb') as out_file:
                for i, chunk_path in enumerate(chunks):
                    logging.debug(f"📥 Processing chunk {i+1}/{len(chunks)}: {chunk_path}")
                    
                    if not os.path.exists(chunk_path):
                        logging.error(f"🚨 Missing chunk: {chunk_path}")
                        return False
                        
                    chunk_size = os.path.getsize(chunk_path)
                    logging.debug(f"📦 Chunk size: {chunk_size} bytes")
                    
                    with open(chunk_path, 'rb') as chunk_file:
                        chunk_data = chunk_file.read()
                        out_file.write(chunk_data)
                        total_written += len(chunk_data)
                        logging.debug(f"✍️ Wrote {len(chunk_data)} bytes (total: {total_written}) in chunk {i+1}")
                    
                    # Validate incremental write
                    current_size = os.path.getsize(output_path)
                    if current_size != total_written:
                        logging.error(f"🚨 Size mismatch after chunk {i+1}! {current_size} vs {total_written}")
                        return False
                    
                    # Delete chunk after successful write
                    logging.debug(f"🗑️ Removing chunk: {chunk_path}")
                    os.remove(chunk_path)
            
            # Final size validation
            if total_written != expected_size:
                logging.error(f"🚨 Final size mismatch! Expected {expected_size}, got {total_written}")
                return False
            
            logging.info(f"✅ Successfully reconstructed {output_path} ({total_written} bytes)")
            return True
        except Exception as e:
            logging.error(f"🚨 Reconstruction failed: {str(e)}")
            return False

    def restore_archive_files(self, directory: str) -> None:
        """Restore original RAR files from chunks"""
        logging.info(f"🔄 Starting archive restoration in {directory}")
        
        # Group chunks by their original RAR part and precompute sizes
        chunk_groups = {}
        for chunk in glob.glob(os.path.join(directory, f"{self.seed}-*.jpg")):
            try:
                parts = os.path.basename(chunk).split('-')
                original_part_index = int(parts[2])
                subindex = int(parts[3].split('.')[0])
                
                if original_part_index not in chunk_groups:
                    chunk_groups[original_part_index] = []
                
                # Store with size and subindex before deletion
                chunk_groups[original_part_index].append({
                    "path": chunk,
                    "size": os.path.getsize(chunk),
                    "subindex": subindex
                })
                
            except (IndexError, ValueError) as e:
                logging.error(f"Invalid chunk format: {chunk} - {e}")
                continue

        # Reconstruct parts in original order
        for part_index in sorted(chunk_groups.keys()):
            # Sort chunks by subindex and extract paths
            sorted_chunks = sorted(chunk_groups[part_index], key=lambda x: x["subindex"])
            chunk_paths = [c["path"] for c in sorted_chunks]
            expected_size = sum(c["size"] for c in sorted_chunks)
            
            # Always use part numbering starting from 1
            output_name = f"archive.part{part_index + 1}.rar"
            output_path = os.path.join(directory, output_name)
            
            logging.info(f"🔧 Reconstructing {output_name} from {len(chunk_paths)} chunks")
            
            if self._reconstruct_file(chunk_paths, output_path, expected_size):
                # Verify RAR integrity
                try:
                    with rarfile.RarFile(output_path) as rf:
                        if rf.testrar():
                            logging.info(f"✅ Verified RAR integrity: {output_name}")
                        else:
                            logging.error(f"🚨 Corrupted RAR: {output_name}")
                except Exception as e:
                    logging.error(f"🚨 RAR verification failed: {str(e)}") 
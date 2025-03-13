# crypto/modules/archives/archive_parts_randomization/archive_parts_splitter.py

import os
from typing import List
import glob
from .archive_parts_randomizer import ArchivePartsRandomizer
from ...wrapers.logging import logging
from ...constants import Msg
import random
import re
import hashlib
import math

class ArchivePartsSplitter(ArchivePartsRandomizer):
    def __init__(self, seed: str = None, min_chunk_ratio: float = 0.7):
        super().__init__(seed, min_chunk_ratio)
        pass

    def _split_file(self, file_path: str, index: int, piece_size: int) -> List[str]:
        """Split a file into random-sized chunks using seed-based randomization"""
        logging.info(f"🔵 Starting split of {file_path} (index {index})")
        logging.debug(f"Initial parameters - piece_size: {piece_size}, seed: {self.seed}")
        
        if not os.path.exists(file_path):
            logging.error(f"🚨 File does not exist: {file_path}")
            return []
            
        file_size = os.path.getsize(file_path)
        logging.info(f"📁 File size: {file_size} bytes")
        directory = os.path.dirname(file_path)
        chunks = []
        
        logging.debug(f"File size: {file_size}, directory: {directory}")
        
        estimated_total_chunks = max(1, math.ceil(file_size / (piece_size * self.min_chunk_ratio)))
        logging.info(f"📈 Estimated chunks: {estimated_total_chunks} based on {piece_size} byte piece size")
        
        with open(file_path, 'rb') as f:
            position = 0
            chunk_index = 0
            
            while position < file_size:
                remaining = file_size - position
                max_possible = min(piece_size, remaining)
                
                # Get random chunk size
                chunk_size = self._get_random_chunk_size(
                    max_size=max_possible,
                    piece_size=piece_size,
                    chunk_index=chunk_index + index * 1000
                )
                logging.debug(f"🔢🔢 Chunk {chunk_index + 1} size: {chunk_size} bytes")
                
                # Ensure we don't exceed remaining bytes
                chunk_size = min(chunk_size, remaining)
                chunk_data = f.read(chunk_size)
                
                chunk_name = self._generate_archive_name(file_path, index, chunk_index)
                chunk_path = os.path.join(directory, chunk_name)
                logging.debug(f"Writing chunk to: {chunk_path}")
                
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(chunk_data)
                    logging.debug(f"✍️ Wrote chunk {chunk_index + 1} ({len(chunk_data)} bytes) to {chunk_path}")
                
                # After writing each chunk
                actual_size = os.path.getsize(chunk_path)
                if actual_size == len(chunk_data):
                    logging.debug(f"✅ Chunk size verified: {actual_size} bytes")
                else:
                    logging.error(f"🚨 Chunk size mismatch! Expected {len(chunk_data)}, got {actual_size}")
                
                chunks.append(chunk_path)
                position += chunk_size
                chunk_number = chunk_index + 1  # 1-based numbering for user display
                logging.debug(f"🔢 Processing chunk {chunk_number}/{estimated_total_chunks}")
                progress_pct = min(position / file_size * 100, 100)  # Cap at 100%
                logging.info(f"📊 File progress: {progress_pct:.1f}% ({position}/{file_size} bytes) - Chunk {chunk_number}")
                chunk_index += 1
        
        # Delete original file after splitting
        logging.debug(f"Removing original file: {file_path}")
        os.remove(file_path)
        chunk_count = chunk_index
        plural = "chunk" if chunk_count == 1 else "chunks"
        logging.info(f"✅ Successfully split {file_path} into {chunk_count} {plural}")
        logging.debug(f"🔍 Total original size: {file_size} bytes")
        logging.debug(f"🔍 Total chunked size: {sum(os.path.getsize(c) for c in chunks)} bytes")
        return chunks

    def randomize_archive_files(self, archive_base_path: str, piece_size: int) -> None:
        """Rename and split RAR parts into random-sized chunks"""
        if not self.seed:
            return
            
        # Convert to absolute path and normalize
        archive_base_path = os.path.abspath(archive_base_path)
        directory = os.path.dirname(archive_base_path)
        if not directory:
            directory = '.'
            
        # Check for existing chunks using seed-based pattern
        if glob.glob(os.path.join(directory, f"{self.seed}-*")):
            logging.error(f"🚨 Found existing chunks for seed '{self.seed}'. Clean up previous chunks or use new seed.")
            return
            
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
            
        # Get all RAR parts using seed-based pattern
        part_pattern = os.path.join(directory, f"{self.seed}-*")
        archive_files = glob.glob(part_pattern)
        
        # If no seed-based chunks found, fall back to original RAR parts pattern
        if not archive_files:
            base_name = os.path.basename(archive_base_path)
            part_pattern = os.path.join(directory, f"{base_name}.part*.rar")
            archive_files = glob.glob(part_pattern)
            
            # Add first archive if it exists
            first_archive = os.path.join(directory, f"{base_name}.rar")
            if os.path.exists(first_archive):
                archive_files.insert(0, first_archive)
        
        if not archive_files:
            logging.warning(Msg.Warn.no_archive_files_found(archive_base_path))
            return
            
        # Process each archive file
        archive_files = sorted([os.path.abspath(f) for f in archive_files])
        for i, archive_file in enumerate(archive_files):
            if self.seed in archive_file:
                logging.warning(f"⚠️ Skipping already processed file: {archive_file}")
                continue
            try:
                chunks = self._split_file(archive_file, i, piece_size)
                logging.info(Msg.Info.split_archive_part(
                    os.path.basename(archive_file),
                    len(chunks)
                ))
            except Exception as e:
                logging.error(Msg.Err.splitting_archive_part(archive_file, str(e)))
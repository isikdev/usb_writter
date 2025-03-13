from typing import List, Optional, Tuple
import os
from creedsolo.creedsolo import RSCodec, ReedSolomonError
from ..winDiskHandler import DiskHandler
from ..constants import Msg
from ..wrapers.logging import logging as log
from tqdm import tqdm


class PartitionHandler:
    MAX_BLOCK_SIZE = 255  # Reed-Solomon limitation

    def __init__(self, partition_letter: str, recovery_percent: int = 10, buffer_size: int = 128 * 1024):

        if not 1 <= recovery_percent <= 100:
            raise ValueError("Recovery percentage must be between 1 and 100")

        if buffer_size % 512 != 0:
            log.warning(
                "Buffer size is not divisible by 512, rounding up to the next multiple of 512")

        self.disk_handler = DiskHandler(partition_letter, buffer_size)
        self.buffer_size = buffer_size
        self.recovery_percent = recovery_percent

        # Get partition size
        self.partition_size = self.disk_handler.get_disk_size()

        # Calculate Reed-Solomon parameters based on recovery percentage
        # parity_size = (recovery_percent/100) * MAX_BLOCK_SIZE
        # But ensure parity_size is strictly less than MAX_BLOCK_SIZE
        self.parity_size = min(
            int(self.MAX_BLOCK_SIZE * recovery_percent / 100), self.MAX_BLOCK_SIZE - 1)
        self.data_size = self.MAX_BLOCK_SIZE - self.parity_size

        log.info(f"Initializing RS codec with {self.parity_size} parity bytes "
                 f"({recovery_percent}% recovery) per {self.data_size} data bytes")

        # Initialize Reed-Solomon codec with calculated parameters
        self.rs = RSCodec(self.parity_size)

    def _read_buffer(self, offset: int) -> bytes:
        return self.disk_handler.read_data(offset, self.buffer_size)

    def _write_buffer(self, offset: int, data: bytes) -> None:
        self.disk_handler.write_data(offset, data)

    def create_parity(self, output_file: str) -> None:
        log.info(f"Creating {self.recovery_percent}% parity data for partition {
                 self.disk_handler.disk_letter}")
        log.info(f"Partition size: {self.partition_size} bytes")
        log.info(f"Buffer size: {self.buffer_size} bytes")

        # Calculate number of full buffers needed
        total_buffers = (self.partition_size +
                         self.buffer_size - 1) // self.buffer_size
        log.info(f"Total buffers to process: {total_buffers}")

        with open(output_file, 'wb') as f:
            # Write header with recovery percentage and buffer size for verification
            f.write(self.recovery_percent.to_bytes(4, 'little'))
            f.write(self.buffer_size.to_bytes(8, 'little'))

            # Create progress bar
            with tqdm(total=total_buffers, desc="Processing buffers", unit="buffer") as pbar:
                for buffer_idx in range(total_buffers):
                    buffer_offset = buffer_idx * self.buffer_size

                    # Read full buffer
                    buffer_data = self._read_buffer(buffer_offset)
                    actual_buffer_size = len(buffer_data)

                    if actual_buffer_size == 0:
                        log.warning(f"Buffer {buffer_idx} is empty, skipping")
                        pbar.update(1)
                        continue

                    # Process buffer in chunks of data_size bytes
                    chunks = [buffer_data[i:i + self.data_size]
                              for i in range(0, len(buffer_data), self.data_size)]
                    all_parity = bytearray()

                    # Generate parity for each chunk
                    for chunk in chunks:
                        chunk_array = bytearray(chunk)
                        # Pad last chunk if needed
                        if len(chunk_array) < self.data_size:
                            chunk_array.extend(
                                [0] * (self.data_size - len(chunk_array)))
                        encoded = self.rs.encode(chunk_array)
                        # Get only parity bytes
                        parity = encoded[len(chunk_array):]
                        all_parity.extend(parity)

                    # Save buffer index and parity
                    f.write(buffer_idx.to_bytes(8, 'little'))
                    f.write(len(all_parity).to_bytes(
                        8, 'little'))  # Store parity size
                    f.write(all_parity)

                    pbar.update(1)

    def verify_and_repair(self, parity_file: str) -> Tuple[int, int]:
        log.info(f"Verifying partition data using parity file {parity_file}")

        errors_found = 0
        errors_corrected = 0

        with open(parity_file, 'rb') as f:
            # Read and verify recovery percentage and buffer size
            stored_recovery = int.from_bytes(f.read(4), 'little')
            stored_buffer_size = int.from_bytes(f.read(8), 'little')

            if stored_recovery != self.recovery_percent:
                raise ValueError(Msg.Err.parity_created_with_dif_recovery_percent(
                    self.recovery_percent, stored_recovery))
            if stored_buffer_size != self.buffer_size:
                raise ValueError(Msg.Err.parity_created_with_dif_buffer_size(
                    self.buffer_size, stored_buffer_size))

            # Calculate total buffers based on partition size, same as in create_parity
            total_buffers = (self.partition_size +
                             self.buffer_size - 1) // self.buffer_size
            log.info(f"Total buffers to verify: {total_buffers}")

            # Read and process each buffer's parity
            with tqdm(total=total_buffers, desc="Verifying data", unit="buffer") as pbar:
                while True:
                    # Read buffer index and parity size
                    index_data = f.read(8)
                    if not index_data:
                        break

                    buffer_idx = int.from_bytes(index_data, 'little')
                    parity_size = int.from_bytes(f.read(8), 'little')
                    all_parity = f.read(parity_size)

                    # Read corresponding buffer from disk
                    buffer_offset = buffer_idx * self.buffer_size
                    buffer_data = self._read_buffer(buffer_offset)

                    if not buffer_data:
                        pbar.update(1)
                        continue

                    # Quick check - encode the buffer and compare parity
                    chunks = [buffer_data[i:i + self.data_size]
                              for i in range(0, len(buffer_data), self.data_size)]
                    current_parity = bytearray()
                    needs_repair = False

                    # Generate and compare parity for each chunk
                    for chunk_idx, chunk in enumerate(chunks):
                        chunk_array = bytearray(chunk)
                        if len(chunk_array) < self.data_size:
                            chunk_array.extend(
                                [0] * (self.data_size - len(chunk_array)))

                        encoded = self.rs.encode(chunk_array)
                        chunk_parity = encoded[len(chunk_array):]
                        current_parity.extend(chunk_parity)

                        # Compare with stored parity
                        stored_chunk_parity = all_parity[chunk_idx * self.parity_size:(
                            chunk_idx + 1) * self.parity_size]
                        if chunk_parity != stored_chunk_parity:
                            needs_repair = True
                            break

                    # Only attempt repair if parity mismatch detected
                    if needs_repair:
                        corrected_buffer = bytearray()
                        buffer_corrected = False
                        parity_chunks = [all_parity[i:i + self.parity_size]
                                         for i in range(0, len(all_parity), self.parity_size)]

                        # Process each chunk
                        for chunk_idx, (chunk, parity) in enumerate(zip(chunks, parity_chunks)):
                            chunk_array = bytearray(chunk)
                            if len(chunk_array) < self.data_size:
                                chunk_array.extend(
                                    [0] * (self.data_size - len(chunk_array)))

                            # Combine chunk with its parity
                            full_data = chunk_array + bytearray(parity)

                            try:
                                # Attempt to decode and correct
                                decoded, _, errata_pos = self.rs.decode(
                                    full_data)
                                errors_list = [
                                    pos for pos in errata_pos if pos < len(chunk)]

                                if errors_list:  # If errors were found in actual data
                                    errors_found += len(errors_list)
                                    buffer_corrected = True
                                    log.warning(f"Found {len(errors_list)} errors in chunk {
                                                chunk_idx} of buffer {buffer_idx}")

                                # Add decoded chunk to corrected buffer
                                corrected_buffer.extend(decoded[:len(chunk)])

                            except ReedSolomonError as e:
                                log.error(f"Unable to correct errors in chunk {
                                          chunk_idx} of buffer {buffer_idx}: {str(e)}")
                                errors_found += 1
                                corrected_buffer.extend(chunk)

                        # Write back corrected buffer if needed
                        if buffer_corrected:
                            self._write_buffer(
                                buffer_offset, bytes(corrected_buffer))
                            errors_corrected += 1
                            log.warning(
                                f"Corrected errors in buffer {buffer_idx}")

                    pbar.update(1)

        return errors_found, errors_corrected

    def close(self):
        self.disk_handler.close_disk()

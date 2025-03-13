from ..winDiskHandler import DiskHandler
from ..wrapers.logging import logging as log
import win32file
import struct
import wmi


class GPTHandler:
    def __init__(self, disk_path: str) -> None:
        self.disk_path = disk_path
        self.handle = None
        self.sector_size = 512  

    def open_disk(self) -> bool:
        try:
            self.handle = win32file.CreateFile(
                self.disk_path, 
                win32file.GENERIC_READ, 
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE, 
                None, 
                win32file.OPEN_EXISTING, 
                0, 
                0
            )
            return True
        except Exception as e:
            print(f"Error opening disk: {e}")
            return False

    def read_gpt_header(self, sector_data: bytes = None) -> dict:
        if not self.handle:
            self.open_disk()

        try:
            # Parse key GPT header information
            return {
                'signature': sector_data[0:8].decode('ascii', errors='ignore'),
                'revision': struct.unpack('<I', sector_data[8:12])[0],
                'gpt_header_size': struct.unpack('<I', sector_data[12:16])[0],
                'crc32_header': struct.unpack('<I', sector_data[16:20])[0],
                'first_usable_lba': struct.unpack('<Q', sector_data[40:48])[0],
                'last_usable_lba': struct.unpack('<Q', sector_data[48:56])[0],
                'disk_guid': sector_data[56:72].hex(),
            }
        except Exception as e:
            print(f"Error reading GPT header: {e}")
            return None

    def get_disk_info(self) -> dict:
        if not self.handle:
            self.open_disk()

        try:
            # Get disk size using DeviceIoControl
            IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C
            buf = win32file.DeviceIoControl(
                self.handle,
                IOCTL_DISK_GET_LENGTH_INFO,
                None,
                8
            )
            disk_size = struct.unpack('Q', buf)[0]  # Unpack as 64-bit integer
            
            # Total sectors calculation
            total_sectors = disk_size // self.sector_size

            gpt_header = self.read_gpt_header()
            
            return {
                'total_sectors': total_sectors,
                'disk_size_bytes': disk_size,
                'sector_size': self.sector_size,
                'first_usable_sector': gpt_header['first_usable_lba'] if gpt_header else None,
                'last_usable_sector': gpt_header['last_usable_lba'] if gpt_header else None,
            }
        except Exception as e:
            print(f"Error getting disk info: {e}")
            return None

    def save_gpt_header(self, filename: str) -> None:
        log.info(f"Saving GPT header to {filename}")

        handle = DiskHandler(self.disk_path, 512)
        
        # Read primary GPT
        gpt_header_data = handle.read_sector(1, 512)
        gpt_header = self.read_gpt_header(gpt_header_data)

        first_usable_lba = gpt_header['first_usable_lba']
        last_usable_lba = gpt_header['last_usable_lba']
        
        gpt_partition_data = handle.read_sector(0, 512 * first_usable_lba)  # MBR + GPT Header + Partition entries
        
        # Read backup GPT (located at the end of the disk)
        backup_partition_entries = handle.read_sector(last_usable_lba, 512 * first_usable_lba)  # Backup partition entries
        backup_gpt_header = handle.read_sector(last_usable_lba + first_usable_lba - 1, 512)  # Backup GPT header
        
        # Save all data to file
        with open(filename, 'w') as f:
            # Save primary GPT info
            f.write("=== Primary GPT ===\n")
            for key, value in gpt_header.items():
                f.write(f"{key}: {value}\n")
            f.write("\nprimary_partition_data: ")
            f.write(gpt_partition_data.hex())
            
            # Save backup GPT info
            f.write("\n\n=== Backup GPT ===\n")
            backup_header = self.read_gpt_header(backup_gpt_header)
            for key, value in backup_header.items():
                f.write(f"{key}: {value}\n")
            f.write("\nbackup_partition_data: ")
            f.write(backup_partition_entries.hex())
            f.write("\nbackup_header_data: ")
            f.write(backup_gpt_header.hex())
        log.info(f"Saved GPT header to {filename}")
        
    
    def verify_gpt_header(self, filename: str) -> bool:
        handle = DiskHandler(self.disk_path, 512)

        # Read saved data
        with open(filename, 'r') as f:
            content = f.read()
            primary_section, backup_section = content.split("=== Backup GPT ===")
            first_usable_lba = None
            last_usable_lba = None
            
            # Parse primary GPT section
            for line in primary_section.split('\n'):
                if line.startswith('first_usable_lba:'):
                    first_usable_lba = int(line.strip().split(':', 1)[1].strip())
                elif line.startswith('last_usable_lba:'):
                    last_usable_lba = int(line.strip().split(':', 1)[1].strip())

            # Read current primary GPT
            gpt_header_data = handle.read_sector(1, 512)
            gpt_header = self.read_gpt_header(gpt_header_data)
            gpt_partition_data = handle.read_sector(0, 512 * first_usable_lba)
            
            # Read current backup GPT
            backup_partition_entries = handle.read_sector(last_usable_lba, 512 * first_usable_lba)  # Backup partition entries
            backup_gpt_header = handle.read_sector(last_usable_lba + first_usable_lba - 1, 512)  # Backup GPT header
            
            # Parse primary GPT section
            saved_primary_header = {}
            for line in primary_section.split('\n'):
                if line.startswith('primary_partition_data:'):
                    saved_primary_partition_data = line.strip().split(':', 1)[1].strip()
                elif ':' in line and not line.startswith('==='):
                    key, value = line.strip().split(':', 1)
                    saved_primary_header[key] = value.strip()
            
            # Parse backup GPT section
            saved_backup_header = {}
            saved_backup_partition_data = None
            saved_backup_header_data = None
            for line in backup_section.split('\n'):
                if line.startswith('backup_partition_data:'):
                    saved_backup_partition_data = line.strip().split(':', 1)[1].strip()
                elif line.startswith('backup_header_data:'):
                    saved_backup_header_data = line.strip().split(':', 1)[1].strip()
                elif ':' in line:
                    key, value = line.strip().split(':', 1)
                    saved_backup_header[key] = value.strip()
            
            # Verify primary GPT
            for key, value in gpt_header.items():
                if str(value) != saved_primary_header.get(key, ''):
                    log.warning(f"Primary GPT mismatch in {key}:")
                    log.warning(f"  Saved: {saved_primary_header.get(key, 'Not found')}")
                    log.warning(f"  Current: {value}")
                    return False
                    
            if gpt_partition_data.hex() != saved_primary_partition_data:
                log.warning("Primary partition data mismatch")
                return False
                
            if backup_gpt_header.hex() != saved_backup_header_data:
                log.warning("Backup GPT header mismatch")
                return False
                
            log.info("GPT header verified successfully")
            return True

    def restore_gpt_header(self, filename: str) -> None:
        log.info(f"Restoring GPT header from {filename}")
        
        handle = DiskHandler(self.disk_path, 512)
        with open(filename, 'r') as f:
            content = f.read()
            primary_section, backup_section = content.split("=== Backup GPT ===")
            first_usable_lba = None
            last_usable_lba = None
            
            # Parse primary GPT section
            for line in primary_section.split('\n'):
                if line.startswith('first_usable_lba:'):
                    first_usable_lba = int(line.strip().split(':', 1)[1].strip())
                elif line.startswith('last_usable_lba:'):
                    last_usable_lba = int(line.strip().split(':', 1)[1].strip())
            
            # Parse primary GPT section 
            for line in primary_section.split('\n'):
                if line.startswith('primary_partition_data:'):
                    primary_partition_data = line.strip().split(':', 1)[1].strip()
            
            # Parse backup GPT section
            for line in backup_section.split('\n'):
                if line.startswith('backup_partition_data:'):
                    backup_partition_data = line.strip().split(':', 1)[1].strip()
                elif line.startswith('backup_header_data:'):
                    backup_gpt_header = line.strip().split(':', 1)[1].strip()
            
            # Restore primary GPT
            handle.write_data(0, bytes.fromhex(primary_partition_data))
            
            # Restore backup GPT
            handle.write_data(last_usable_lba, bytes.fromhex(backup_partition_data))
            handle.write_data(last_usable_lba + len(backup_partition_data), bytes.fromhex(backup_gpt_header))
            
        log.info("GPT header restored successfully")

    def close(self):
        """Close disk handle"""
        if self.handle:
            win32file.CloseHandle(self.handle)
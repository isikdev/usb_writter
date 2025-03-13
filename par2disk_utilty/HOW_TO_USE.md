# Par2Disk CLI Utility - How to Use

Par2Disk is a utility for creating and managing parity files for disk partitions and GPT (GUID Partition Table). This tool helps you backup and restore disk structures in case of corruption.

## Prerequisites

- Python 3.x
- Appropriate permissions to access disk devices

## Basic Commands

### 1. Creating Parity Files

#### Create both GPT and partition parity files:

```bash
python par2disk_utility.py create --disk-letter L --physic-number 1 --type both
```

#### Create only GPT parity file:

```bash
./par2disk_utility.py create --disk-letter D --physic-number 1 --type gpt
```

#### Create only partition parity file:

```bash
./par2disk_utility.py create --disk-letter D --physic-number 1 --type partition
```

### 2. Verifying and Restoring

#### Verify and restore both GPT and partition:

```bash
python par2disk_utility.py verify --disk-letter L --physic-number 1 --type both
```

#### Verify and restore only GPT:

```bash
./par2disk_utility.py verify --disk-letter D --physic-number 1 --type gpt
```

#### Verify and restore only partition:

```bash
./par2disk_utility.py verify --disk-letter D --physic-number 1 --type partition
```

## Command Arguments

Required arguments:

- `--disk-letter`: The drive letter to operate on (e.g., C, D)
- `--physic-number`: Physical drive number
- `--type`: Type of operation:
  - `gpt`: Only GPT operations
  - `partition`: Only partition operations
  - `both`: Both GPT and partition operations

Optional arguments:

- `--buffer-size`: Buffer size for operations in bytes (default: 1MB)
- `--gpt-file`: Base filename for GPT parity (default: disk_gpt)
- `--partition-file`: Base filename for partition parity (default: disk_part)
- `--recovery-percent`: Recovery data percentage (default: 10)

## Output Files

The utility creates the following files:

- GPT parity file: `[gpt-file].gpt`
- Partition parity file: `[partition-file].part`

## Error Handling

The utility will:

1. Display disk information before operations
2. Show progress and status messages during operations
3. Exit with appropriate error messages if something goes wrong

## Common Issues

1. **Permission denied**: Run the utility with appropriate permissions to access disk devices
2. **Invalid disk letter**: Make sure the specified disk letter exists and is accessible
3. **Invalid physical drive number**: Ensure the physical drive number is correct
4. **Parity files not found during verify**: Ensure parity files exist in the expected location

## Best Practices

1. Always create fresh parity files after significant disk changes
2. Store parity files on a different physical drive
3. Regularly verify the integrity of your disks
4. Test the restore process in a safe environment first

## Support

If you encounter any issues or need assistance:

1. Check the error messages in the console output
2. Ensure you have the necessary permissions
3. Double-check the disk letter and physical drive number
4. Verify the parity files exist in the expected location

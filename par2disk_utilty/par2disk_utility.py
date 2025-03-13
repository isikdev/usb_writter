#!/usr/bin/env python3

import argparse
import sys
from par2disk.par2disk import Par2Disk

def create_parser():
    parser = argparse.ArgumentParser(
        description='Par2Disk Utility - Create and verify parity files for disk partitions and GPT',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Common arguments for both commands
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument('--disk-letter', required=True, help='Disk letter (e.g., C, D)')
    common_args.add_argument('--physic-number', type=int, required=True, help='Physical drive number')
    common_args.add_argument('--buffer-size', type=int, default=1024*1024, help='Buffer size for operations (default: 1MB)')
    common_args.add_argument('--gpt-file', default='disk_gpt', help='Base filename for GPT parity (default: disk_gpt)')
    common_args.add_argument('--partition-file', default='disk_parity', help='Base filename for partition parity (default: disk_parity)')
    common_args.add_argument('--recovery-percent', type=int, default=30, help='Recovery data percentage (default: 30)')
    
    # Create parity command
    create_parser = subparsers.add_parser('create', parents=[common_args], help='Create parity files')
    create_parser.add_argument('--type', choices=['gpt', 'partition', 'both'], required=True,
                             help='Type of parity to create (gpt, partition, or both)')

    # Verify and restore command
    verify_parser = subparsers.add_parser('verify', parents=[common_args], help='Verify and restore from parity files')
    verify_parser.add_argument('--type', choices=['gpt', 'partition', 'both'], required=True,
                             help='Type of verification to perform (gpt, partition, or both)')
    
    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        # Initialize Par2Disk
        par2disk = Par2Disk(
            disk_letter=args.disk_letter,
            physic_number=args.physic_number,
            recovery_percent=args.recovery_percent,
            gpt_save_file=args.gpt_file,
            partition_save_file=args.partition_file,
            buffer_size=args.buffer_size
        )
        
        if not par2disk.can_continue:
            print("Error: Failed to initialize Par2Disk")
            sys.exit(1)

        # Display disk information
        par2disk.display_disk_info()

        if args.command == 'create':
            if args.type in ['gpt', 'both']:
                print("Creating GPT parity file...")
                par2disk.create_parity_gpt()
            
            if args.type in ['partition', 'both']:
                print("Creating partition parity file...")
                par2disk.create_parity_partition()

        elif args.command == 'verify':
            if args.type in ['gpt', 'both']:
                print("Verifying and repairing GPT...")
                par2disk.verify_and_repair_gpt()
            
            if args.type in ['partition', 'both']:
                print("Verifying and repairing partition...")
                par2disk.verify_and_repair_partition()

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
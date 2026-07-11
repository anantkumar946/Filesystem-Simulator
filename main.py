#!/usr/bin/env python3
"""
Entry point for the simulator.
Run: python main.py
"""
import os
from storage.virtual_disk import VirtualDisk
from filesystems.fat32 import FAT32
from filesystems.ext4 import Ext4
from filesystems.ntfs import NTFS
from utils.performance_metrics import Perf

FS_MAP = {
    '1': ('FAT32', FAT32),
    '2': ('EXT4', Ext4),
    '3': ('NTFS', NTFS),
}

def choose_fs():
    print("Choose file system type:")
    for k, v in FS_MAP.items():
        print(f"{k}. {v[0]}")
    choice = input('> ').strip()
    return FS_MAP.get(choice)


def repl(fs_instance):
    print('\nEnter commands: create <name> <size_kb>, write <name> <data>, read <name>, delete <name>, list, info, exit')
    while True:
        cmd = input('> ').strip()
        if not cmd:
            continue
        parts = cmd.split(maxsplit=2)
        op = parts[0].lower()
        try:
            if op == 'create' and len(parts) >= 3:
                name = parts[1]
                size_kb = int(parts[2])
                fs_instance.create_file(name, size_kb*1024)
            elif op == 'write' and len(parts) >= 3:
                name = parts[1]
                data = parts[2].encode('utf-8')
                fs_instance.write_file(name, data)
            elif op == 'read' and len(parts) >= 2:
                print(fs_instance.read_file(parts[1]))
            elif op == 'delete' and len(parts) >= 2:
                fs_instance.delete_file(parts[1])
            elif op == 'list':
                for entry in fs_instance.list_files():
                    print(entry)
            elif op == 'info':
                print(fs_instance.info())
            elif op == 'exit':
                fs_instance.close()
                break
            else:
                print('Unknown or malformed command')
        except Exception as e:
            print('Error:', e)


if __name__ == '__main__':
    print('--- Cross-Platform File System Simulator ---')
    fs_choice = choose_fs()
    if not fs_choice:
        print('Invalid choice; exiting')
        exit(1)

    fs_name, fs_class = fs_choice
    disk_path = f'virtual_disk_{fs_name.lower()}.bin'
    # Create a 10MB disk if not present
    disk = VirtualDisk(disk_path, size_bytes=10 * 1024 * 1024, block_size=4096)
    fs = fs_class(disk)
    repl(fs)
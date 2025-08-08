#!/usr/bin/env python3
"""
Script to clean up duplicate hostname entries in the py-perf system.

This script helps identify and remove duplicate hostname entries that may
have been created due to hostname changes or different collection methods.
"""

import os
import sys
import json
from datetime import datetime

# Add Django path
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pyperfweb.settings')

import django
django.setup()

from pyperfweb.dashboard.registry_service import SystemRegistryService
import boto3


def main():
    print("🔍 PyPerf Hostname Duplicate Cleanup Tool")
    print("=" * 50)
    
    # Get all systems from registry
    registry = SystemRegistryService()
    systems = registry.get_all_systems()
    
    print(f"Found {len(systems)} systems in registry:")
    for i, system in enumerate(systems, 1):
        hostname = system.get('hostname', 'unknown')
        status = system.get('status', 'unknown')
        platform = system.get('platform', 'Unknown')
        first_seen = system.get('first_seen', 0)
        last_seen = system.get('last_seen', 0)
        
        first_seen_date = datetime.fromtimestamp(first_seen).strftime('%Y-%m-%d %H:%M:%S') if first_seen else 'Unknown'
        last_seen_date = datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M:%S') if last_seen else 'Unknown'
        
        print(f"\n{i}. Hostname: {hostname}")
        print(f"   Status: {status}")
        print(f"   Platform: {platform}")
        print(f"   First Seen: {first_seen_date}")
        print(f"   Last Seen: {last_seen_date}")
    
    if len(systems) <= 1:
        print("\n✅ No duplicate hostnames found!")
        return
    
    print(f"\n🔧 Manual Cleanup Options:")
    print("=" * 30)
    
    # Show which hostnames to potentially remove
    systems_by_last_seen = sorted(systems, key=lambda x: x.get('last_seen', 0), reverse=True)
    
    print("Recommended action based on last activity:")
    for i, system in enumerate(systems_by_last_seen):
        hostname = system.get('hostname')
        last_seen = system.get('last_seen', 0)
        status = system.get('status', 'unknown')
        
        if i == 0:
            print(f"  ✅ KEEP: {hostname} (most recent, {status})")
        else:
            print(f"  ❌ REMOVE: {hostname} (older, {status})")
    
    print(f"\nTo remove a hostname from the registry, run:")
    print(f"curl -X POST http://localhost:8000/api/system/remove/ \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"hostname\": \"HOSTNAME_TO_REMOVE\"}}'")
    
    print(f"\nOr remove from Django shell:")
    print(f"python manage.py shell -c \"")
    print(f"from pyperfweb.dashboard.registry_service import SystemRegistryService")
    print(f"registry = SystemRegistryService()")
    print(f"registry.remove_system('HOSTNAME_TO_REMOVE')")
    print(f"\"")
    
    # Interactive removal option
    print(f"\n🚀 Interactive Removal")
    print("=" * 20)
    
    while True:
        choice = input("\nDo you want to remove a hostname now? (y/n): ").lower().strip()
        
        if choice == 'n':
            break
        elif choice == 'y':
            print("\nAvailable hostnames:")
            for i, system in enumerate(systems, 1):
                hostname = system.get('hostname')
                status = system.get('status', 'unknown')
                print(f"  {i}. {hostname} ({status})")
            
            try:
                selection = input(f"\nEnter hostname number to remove (1-{len(systems)}): ").strip()
                index = int(selection) - 1
                
                if 0 <= index < len(systems):
                    hostname_to_remove = systems[index]['hostname']
                    
                    confirm = input(f"\n⚠️  Are you sure you want to remove '{hostname_to_remove}'? (yes/no): ")
                    if confirm.lower() == 'yes':
                        if registry.remove_system(hostname_to_remove):
                            print(f"✅ Successfully removed '{hostname_to_remove}' from registry")
                            # Refresh systems list
                            systems = [s for s in systems if s['hostname'] != hostname_to_remove]
                            if len(systems) <= 1:
                                print("✅ No more duplicates!")
                                break
                        else:
                            print(f"❌ Failed to remove '{hostname_to_remove}'")
                    else:
                        print("Cancelled.")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Please enter a valid number.")
        else:
            print("Please enter 'y' or 'n'")
    
    print("\n✅ Cleanup complete!")


if __name__ == "__main__":
    main()
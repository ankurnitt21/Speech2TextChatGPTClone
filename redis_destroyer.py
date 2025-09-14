#!/usr/bin/env python3
"""
Redis Database Destroyer
========================
A script to safely destroy/clear data from Redis database with multiple safety confirmations.
Includes options for complete destruction or selective deletion by patterns.
"""

import redis
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import sys

# Redis Configuration (extracted from main_controllable.py)
REDIS_CONFIG = {
    'host': 'redis-10748.c330.asia-south1-1.gce.redns.redis-cloud.com',
    'port': 10748,
    'decode_responses': True,
    'username': "default",
    'password': "0LOOmEVVY2jnAUieXYIV5kv7rZhx7ItL",
}

class RedisDestroyer:
    def __init__(self, redis_config: Dict):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(**redis_config)
            # Test connection
            self.redis_client.ping()
            print("✅ Successfully connected to Redis")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            sys.exit(1)
    
    def get_all_keys(self) -> List[str]:
        """Get all keys in the database"""
        return self.redis_client.keys('*')
    
    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """Get keys matching a specific pattern"""
        return self.redis_client.keys(pattern)
    
    def create_backup(self, keys: List[str], filename: Optional[str] = None) -> Optional[str]:
        """Create a backup of specified keys before deletion"""
        if not keys:
            print("⚠️ No keys to backup")
            return None
        
        if filename is None:
            filename = f"redis_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        backup_data = {
            'backup_timestamp': datetime.now().isoformat(),
            'total_keys': len(keys),
            'keys': {}
        }
        
        print(f"💾 Creating backup of {len(keys)} keys...")
        
        for i, key in enumerate(keys, 1):
            try:
                key_type = self.redis_client.type(key)
                ttl = self.redis_client.ttl(key)
                
                # Get value based on type
                if key_type == 'string':
                    value = self.redis_client.get(key)
                elif key_type == 'hash':
                    value = self.redis_client.hgetall(key)
                elif key_type == 'list':
                    value = self.redis_client.lrange(key, 0, -1)
                elif key_type == 'set':
                    value = list(self.redis_client.smembers(key))
                elif key_type == 'zset':
                    value = self.redis_client.zrange(key, 0, -1, withscores=True)
                else:
                    value = f"[UNSUPPORTED TYPE: {key_type}]"
                
                backup_data['keys'][key] = {
                    'type': key_type,
                    'ttl': ttl if ttl != -1 else None,
                    'value': value
                }
                
                if i % 10 == 0:
                    print(f"   Backed up {i}/{len(keys)} keys...")
                    
            except Exception as e:
                print(f"⚠️ Error backing up key '{key}': {e}")
                backup_data['keys'][key] = {
                    'type': 'ERROR',
                    'error': str(e)
                }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
            print(f"✅ Backup created: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def delete_keys(self, keys: List[str]) -> int:
        """Delete specified keys and return count of deleted keys"""
        if not keys:
            return 0
        
        deleted_count = 0
        batch_size = 100  # Delete in batches for better performance
        
        print(f"🗑️ Deleting {len(keys)} keys...")
        
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            try:
                result = self.redis_client.delete(*batch)
                deleted_count += result
                print(f"   Deleted batch {i//batch_size + 1}: {result}/{len(batch)} keys")
            except Exception as e:
                print(f"⚠️ Error deleting batch: {e}")
        
        return deleted_count
    
    def confirm_destruction(self, keys: List[str], operation_type: str) -> bool:
        """Multiple confirmation prompts for safety"""
        print(f"\n{'='*60}")
        print(f"⚠️  DANGER: {operation_type.upper()}")
        print(f"{'='*60}")
        print(f"You are about to DELETE {len(keys)} keys from Redis!")
        print(f"Database: {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
        print(f"{'='*60}")
        
        if len(keys) <= 20:
            print("\nKeys to be deleted:")
            for key in keys:
                print(f"  - {key}")
        else:
            print(f"\nFirst 10 keys to be deleted:")
            for key in keys[:10]:
                print(f"  - {key}")
            print(f"  ... and {len(keys) - 10} more keys")
        
        print(f"\n{'='*60}")
        
        # First confirmation
        try:
            confirm1 = input("Type 'YES' to continue (case-sensitive): ").strip()
            if confirm1 != 'YES':
                print("❌ Operation cancelled")
                return False
            
            # Second confirmation with key count
            confirm2 = input(f"Confirm deletion of {len(keys)} keys by typing the number: ").strip()
            if confirm2 != str(len(keys)):
                print("❌ Operation cancelled - number mismatch")
                return False
            
            # Final confirmation
            print("\n🚨 FINAL WARNING: This action CANNOT be undone!")
            confirm3 = input("Type 'DESTROY' to proceed: ").strip()
            if confirm3 != 'DESTROY':
                print("❌ Operation cancelled")
                return False
            
            return True
            
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user")
            return False
        except Exception:
            print("\n❌ Operation cancelled - input error")
            return False
    
    def destroy_all_data(self, create_backup: bool = True) -> bool:
        """Destroy all data in the Redis database"""
        all_keys = self.get_all_keys()
        
        if not all_keys:
            print("✅ Database is already empty - no keys to delete")
            return True
        
        print(f"🔍 Found {len(all_keys)} keys in the database")
        
        # Create backup if requested
        backup_file = None
        if create_backup:
            backup_choice = input("💾 Create backup before deletion? (y/n): ").lower().strip()
            if backup_choice in ['y', 'yes']:
                backup_file = self.create_backup(all_keys)
                if not backup_file:
                    print("❌ Backup failed. Aborting destruction for safety.")
                    return False
        
        # Confirm destruction
        if not self.confirm_destruction(all_keys, "COMPLETE DATABASE DESTRUCTION"):
            return False
        
        # Perform destruction
        print(f"\n💥 Starting destruction of all {len(all_keys)} keys...")
        start_time = time.time()
        
        deleted_count = self.delete_keys(all_keys)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ DESTRUCTION COMPLETE")
        print(f"{'='*60}")
        print(f"Keys deleted: {deleted_count}/{len(all_keys)}")
        print(f"Duration: {duration:.2f} seconds")
        if backup_file:
            print(f"Backup saved: {backup_file}")
        print(f"{'='*60}")
        
        return deleted_count == len(all_keys)
    
    def destroy_by_pattern(self, pattern: str, create_backup: bool = True) -> bool:
        """Destroy keys matching a specific pattern"""
        matching_keys = self.get_keys_by_pattern(pattern)
        
        if not matching_keys:
            print(f"✅ No keys found matching pattern: {pattern}")
            return True
        
        print(f"🔍 Found {len(matching_keys)} keys matching pattern: {pattern}")
        
        # Create backup if requested
        backup_file = None
        if create_backup:
            backup_choice = input("💾 Create backup before deletion? (y/n): ").lower().strip()
            if backup_choice in ['y', 'yes']:
                backup_file = self.create_backup(matching_keys)
                if not backup_file:
                    print("❌ Backup failed. Aborting destruction for safety.")
                    return False
        
        # Confirm destruction
        if not self.confirm_destruction(matching_keys, f"PATTERN DELETION: {pattern}"):
            return False
        
        # Perform destruction
        print(f"\n💥 Starting deletion of {len(matching_keys)} keys matching '{pattern}'...")
        start_time = time.time()
        
        deleted_count = self.delete_keys(matching_keys)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ PATTERN DELETION COMPLETE")
        print(f"{'='*60}")
        print(f"Pattern: {pattern}")
        print(f"Keys deleted: {deleted_count}/{len(matching_keys)}")
        print(f"Duration: {duration:.2f} seconds")
        if backup_file:
            print(f"Backup saved: {backup_file}")
        print(f"{'='*60}")
        
        return deleted_count == len(matching_keys)
    
    def interactive_menu(self):
        """Interactive menu for destruction options"""
        while True:
            print(f"\n{'='*60}")
            print("🗑️  REDIS DESTRUCTION MENU")
            print(f"{'='*60}")
            print("1. 💥 Destroy ALL data (complete database wipe)")
            print("2. 🎯 Destroy by pattern (e.g., 'image:*', 'temp:*')")
            print("3. 📊 Show database statistics")
            print("4. 🚪 Exit")
            print(f"{'='*60}")
            
            try:
                choice = input("Select option (1-4): ").strip()
                
                if choice == '1':
                    self.destroy_all_data()
                    break
                
                elif choice == '2':
                    pattern = input("Enter pattern (e.g., 'image:*', 'temp:*'): ").strip()
                    if pattern:
                        self.destroy_by_pattern(pattern)
                    else:
                        print("❌ Invalid pattern")
                
                elif choice == '3':
                    all_keys = self.get_all_keys()
                    print(f"\n📊 Database Statistics:")
                    print(f"Total keys: {len(all_keys)}")
                    if all_keys:
                        # Show some sample keys
                        print("Sample keys:")
                        for key in all_keys[:10]:
                            print(f"  - {key}")
                        if len(all_keys) > 10:
                            print(f"  ... and {len(all_keys) - 10} more")
                
                elif choice == '4':
                    print("👋 Exiting...")
                    break
                
                else:
                    print("❌ Invalid choice. Please select 1-4.")
                    
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Main function"""
    print("🚀 Starting Redis Destruction Tool...")
    print("⚠️  WARNING: This tool can permanently delete data!")
    
    # Create destroyer
    destroyer = RedisDestroyer(REDIS_CONFIG)
    
    # Run interactive menu
    destroyer.interactive_menu()


if __name__ == "__main__":
    main()

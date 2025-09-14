#!/usr/bin/env python3
"""
Redis Database Inspector
========================
A comprehensive script to inspect and display all data in a Redis database.
Shows keys, values, data types, memory usage, and provides organized output.
"""

import redis
import json
import base64
from datetime import datetime
from typing import Dict, List, Any, Union
import sys

# Redis Configuration (extracted from main_controllable.py)
REDIS_CONFIG = {
    'host': 'redis-10748.c330.asia-south1-1.gce.redns.redis-cloud.com',
    'port': 10748,
    'decode_responses': True,
    'username': "default",
    'password': "0LOOmEVVY2jnAUieXYIV5kv7rZhx7ItL",
}

class RedisInspector:
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
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get general database information"""
        info = self.redis_client.info()
        return {
            'redis_version': info.get('redis_version', 'Unknown'),
            'used_memory_human': info.get('used_memory_human', 'Unknown'),
            'connected_clients': info.get('connected_clients', 0),
            'total_commands_processed': info.get('total_commands_processed', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
        }
    
    def get_all_keys(self) -> List[str]:
        """Get all keys in the database"""
        return self.redis_client.keys('*')
    
    def get_key_info(self, key: str) -> Dict[str, Any]:
        """Get detailed information about a specific key"""
        try:
            key_type = self.redis_client.type(key)
            ttl = self.redis_client.ttl(key)
            
            # Get memory usage (if supported)
            try:
                memory_usage = self.redis_client.memory_usage(key)
            except:
                memory_usage = None
            
            return {
                'key': key,
                'type': key_type,
                'ttl': ttl if ttl != -1 else 'No expiration',
                'memory_usage': f"{memory_usage} bytes" if memory_usage else "Unknown"
            }
        except Exception as e:
            return {
                'key': key,
                'type': 'ERROR',
                'ttl': f'Error: {e}',
                'memory_usage': 'Unknown'
            }
    
    def get_key_value(self, key: str, key_type: str) -> Any:
        """Get the value of a key based on its type"""
        try:
            if key_type == 'string':
                value = self.redis_client.get(key)
                # Try to detect if it's base64 encoded image
                if key.startswith('image:') and isinstance(value, str):
                    return f"[BASE64 IMAGE DATA - {len(value)} characters]"
                return value
            
            elif key_type == 'hash':
                return self.redis_client.hgetall(key)
            
            elif key_type == 'list':
                return self.redis_client.lrange(key, 0, -1)
            
            elif key_type == 'set':
                return list(self.redis_client.smembers(key))
            
            elif key_type == 'zset':
                return self.redis_client.zrange(key, 0, -1, withscores=True)
            
            elif key_type == 'stream':
                try:
                    # Get last 10 entries from stream
                    entries = self.redis_client.xrange(key, count=10)
                    return f"[STREAM with {len(entries)} recent entries]"
                except:
                    return "[STREAM - unable to read]"
            
            else:
                return f"[UNSUPPORTED TYPE: {key_type}]"
                
        except Exception as e:
            return f"[ERROR READING VALUE: {e}]"
    
    def categorize_keys(self, keys: List[str]) -> Dict[str, List[str]]:
        """Categorize keys by patterns"""
        categories = {
            'Images': [],
            'Channels/PubSub': [],
            'Speech Status': [],
            'System/Config': [],
            'Other': []
        }
        
        for key in keys:
            if key.startswith('image:'):
                categories['Images'].append(key)
            elif 'channel' in key.lower() or 'realtime' in key.lower():
                categories['Channels/PubSub'].append(key)
            elif 'speech' in key.lower():
                categories['Speech Status'].append(key)
            elif key.startswith('config:') or key.startswith('system:'):
                categories['System/Config'].append(key)
            else:
                categories['Other'].append(key)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def format_value_for_display(self, value: Any, max_length: int = 200) -> str:
        """Format value for readable display"""
        if value is None:
            return "None"
        
        if isinstance(value, (dict, list)):
            json_str = json.dumps(value, indent=2, default=str)
            if len(json_str) > max_length:
                return json_str[:max_length] + "...\n[TRUNCATED]"
            return json_str
        
        str_value = str(value)
        if len(str_value) > max_length:
            return str_value[:max_length] + "...\n[TRUNCATED]"
        
        return str_value
    
    def inspect_database(self) -> None:
        """Main inspection function"""
        print("\n" + "="*80)
        print("🔍 REDIS DATABASE INSPECTION REPORT")
        print("="*80)
        print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Database info
        print("\n📊 DATABASE INFORMATION")
        print("-" * 40)
        db_info = self.get_database_info()
        for key, value in db_info.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        
        # Get all keys
        all_keys = self.get_all_keys()
        print(f"\n🔑 TOTAL KEYS FOUND: {len(all_keys)}")
        
        if not all_keys:
            print("❌ No keys found in the database")
            return
        
        # Categorize keys
        categorized_keys = self.categorize_keys(all_keys)
        
        print("\n📂 KEY CATEGORIES")
        print("-" * 40)
        for category, keys in categorized_keys.items():
            print(f"{category}: {len(keys)} keys")
        
        # Detailed key inspection
        print("\n🔍 DETAILED KEY INSPECTION")
        print("="*80)
        
        for category, keys in categorized_keys.items():
            if not keys:
                continue
                
            print(f"\n📁 {category.upper()} ({len(keys)} keys)")
            print("-" * 60)
            
            for key in keys:
                key_info = self.get_key_info(key)
                key_type = key_info['type']
                
                print(f"\n🔑 Key: {key}")
                print(f"   Type: {key_type}")
                print(f"   TTL: {key_info['ttl']}")
                print(f"   Memory: {key_info['memory_usage']}")
                
                if key_type != 'ERROR':
                    value = self.get_key_value(key, key_type)
                    formatted_value = self.format_value_for_display(value)
                    print(f"   Value: {formatted_value}")
                else:
                    print(f"   Value: [ERROR - Could not retrieve]")
                
                print("   " + "-"*50)
        
        print("\n" + "="*80)
        print("✅ INSPECTION COMPLETE")
        print("="*80)
    
    def export_to_json(self, filename: str = None) -> str:
        """Export all data to JSON file"""
        if filename is None:
            filename = f"redis_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'database_info': self.get_database_info(),
            'keys': {}
        }
        
        all_keys = self.get_all_keys()
        for key in all_keys:
            key_info = self.get_key_info(key)
            if key_info['type'] != 'ERROR':
                value = self.get_key_value(key, key_info['type'])
                export_data['keys'][key] = {
                    'info': key_info,
                    'value': value
                }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)
            print(f"📁 Data exported to: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return None


def main():
    """Main function"""
    print("🚀 Starting Redis Database Inspection...")
    
    # Create inspector
    inspector = RedisInspector(REDIS_CONFIG)
    
    # Run inspection
    inspector.inspect_database()
    
    # Ask if user wants to export
    try:
        export_choice = input("\n💾 Would you like to export the data to JSON? (y/n): ").lower().strip()
        if export_choice in ['y', 'yes']:
            inspector.export_to_json()
    except KeyboardInterrupt:
        print("\n👋 Inspection complete!")
    except:
        pass  # Handle any input errors gracefully


if __name__ == "__main__":
    main()

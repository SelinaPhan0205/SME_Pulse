"""
===================================================
Redis Cache Invalidation Script
===================================================
Mục đích: Xóa cache trong Redis sau khi dữ liệu được refresh
Pattern: v1:{org_id}:cash:*, v1:{org_id}:revenue:*
===================================================
"""

import redis
import sys
from typing import List

def invalidate_cache_patterns(patterns: List[str], redis_host='redis', redis_port=6379):
    """
    Xóa các keys trong Redis matching với patterns
    
    Args:
        patterns: List các patterns (hỗ trợ wildcard *)
        redis_host: Redis hostname
        redis_port: Redis port
    """
    try:
        # Kết nối tới Redis
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        # Test connection
        r.ping()
        print(f"✅ Connected to Redis at {redis_host}:{redis_port}")
        
        total_deleted = 0
        
        for pattern in patterns:
            print(f"\n🔍 Tìm kiếm keys matching pattern: {pattern}")
            
            # Scan keys (an toàn hơn KEYS command)
            keys = []
            for key in r.scan_iter(match=pattern, count=100):
                keys.append(key)
            
            if keys:
                print(f"   Tìm thấy {len(keys)} keys")
                deleted = r.delete(*keys)
                total_deleted += deleted
                print(f"   ✅ Đã xóa {deleted} keys")
            else:
                print(f"   ℹ️  Không tìm thấy keys nào")
        
        print(f"\n✨ Hoàn thành! Tổng cộng xóa {total_deleted} keys")
        return total_deleted
        
    except redis.ConnectionError as e:
        print(f"❌ Lỗi kết nối Redis: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Các patterns cần invalidate
    patterns = [
        'v1:*:cash:overview',      # Cache overview của cash flow
        'v1:*:revenue:daily',      # Cache revenue hàng ngày
        'v1:*:orders:summary',     # Cache summary của orders
    ]
    
    print("🗑️  Bắt đầu invalidate Redis cache...")
    print(f"Patterns: {patterns}")
    
    invalidate_cache_patterns(patterns)

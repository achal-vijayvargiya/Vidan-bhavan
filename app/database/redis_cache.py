import redis
import os
import json
from app.logging.logger import Logger

# Initialize logger
logger = Logger()

# Setup Redis connection (adjust host/port/db as needed)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

try:
    redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    # Test connection
    redis_client.ping()
    logger.info("✅ Redis connection established successfully")
except Exception as e:
    logger.error(f"❌ Redis connection failed: {e}")
    redis_client = None

def set_llm_cache(key: str, value, expire_seconds: int = 3600, expiry_hours: int = None):
    """
    Set a value in Redis cache for LLM calls. Value is JSON-serialized.
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        expire_seconds: Expiry time in seconds (default 1 hour)
        expiry_hours: Expiry time in hours (overrides expire_seconds if provided)
    """
    if not redis_client:
        logger.warning("Redis not available, skipping cache set")
        return
    
    try:
        # COST OPTIMIZATION: Support expiry_hours parameter
        if expiry_hours is not None:
            expire_seconds = expiry_hours * 3600
        
        serialized_value = json.dumps(value, ensure_ascii=False)
        redis_client.set(key, serialized_value, ex=expire_seconds)
        logger.info(f"✅ Cached key: {key[:50]}... (expires in {expire_seconds}s)")
    except Exception as e:
        logger.error(f"❌ Error setting cache for key {key}: {e}")

def get_llm_cache(key: str):
    """
    Get a value from Redis cache for LLM calls. Returns deserialized JSON or None.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found/error
    """
    if not redis_client:
        logger.warning("Redis not available, cache miss")
        return None
    
    try:
        val = redis_client.get(key)
        if val is not None:
            logger.info(f"✅ Cache hit for key: {key[:50]}...")
            return json.loads(val)
        else:
            logger.info(f"⚠️  Cache miss for key: {key[:50]}...")
            return None
    except Exception as e:
        logger.error(f"❌ Error getting cache for key {key}: {e}")
        return None

def delete_llm_cache(key: str):
    """
    Delete a value from Redis cache by key.
    
    Args:
        key: Cache key to delete
    """
    if not redis_client:
        logger.warning("Redis not available, skipping cache delete")
        return
    
    try:
        result = redis_client.delete(key)
        if result:
            logger.info(f"✅ Deleted cache key: {key[:50]}...")
        else:
            logger.info(f"⚠️  Cache key not found for deletion: {key[:50]}...")
    except Exception as e:
        logger.error(f"❌ Error deleting cache for key {key}: {e}")

def clear_llm_cache_pattern(pattern: str = "*llm_cache*"):
    """
    Clear all LLM cache entries matching a pattern.
    COST OPTIMIZATION: Use to clear old cache entries.
    
    Args:
        pattern: Pattern to match cache keys (default: "*llm_cache*")
    """
    if not redis_client:
        logger.warning("Redis not available, skipping cache clear")
        return 0
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            deleted_count = redis_client.delete(*keys)
            logger.info(f"✅ Cleared {deleted_count} LLM cache entries matching '{pattern}'")
            return deleted_count
        else:
            logger.info(f"⚠️  No cache entries found matching '{pattern}'")
            return 0
    except Exception as e:
        logger.error(f"❌ Error clearing cache pattern {pattern}: {e}")
        return 0

def get_cache_stats():
    """
    Get Redis cache statistics for monitoring.
    COST OPTIMIZATION: Monitor cache hit rates.
    
    Returns:
        dict: Cache statistics
    """
    if not redis_client:
        return {"error": "Redis not available"}
    
    try:
        info = redis_client.info()
        stats = {
            "total_keys": redis_client.dbsize(),
            "memory_used": info.get("used_memory_human", "Unknown"),
            "cache_hits": info.get("keyspace_hits", 0),
            "cache_misses": info.get("keyspace_misses", 0),
            "connected_clients": info.get("connected_clients", 0)
        }
        
        # Calculate hit rate
        total_requests = stats["cache_hits"] + stats["cache_misses"]
        if total_requests > 0:
            stats["hit_rate"] = round((stats["cache_hits"] / total_requests) * 100, 2)
        else:
            stats["hit_rate"] = 0
            
        logger.info(f"📊 Cache stats: {stats}")
        return stats
    except Exception as e:
        logger.error(f"❌ Error getting cache stats: {e}")
        return {"error": str(e)} 
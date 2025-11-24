from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import json
import logging
from typing import Tuple, List, Dict, Optional

logger = logging.getLogger(__name__)


class QuotaService:
    """
    Service for managing execution quotas using Redis with sliding window.
    """

    EXECUTION_TTL = 86400  # 24 hours in seconds

    def __init__(self):
        self.cache = cache
        # Get raw Redis client for sorted set operations
        try:
            from django_redis import get_redis_connection
            self.redis = get_redis_connection("default")
        except Exception as e:
            logger.error(f"Failed to get Redis connection: {e}")
            self.redis = None
    
    def _get_execution_key(self, tenant_id: str) -> str:
        """Generate Redis key for execution tracking."""
        base_key = f"executions:{tenant_id}"
        # Use cache make_key to get the actual key with prefix
        return self.cache.make_key(base_key) if hasattr(self.cache, 'make_key') else base_key

    def _get_app_count_key(self, tenant_id: str) -> str:
        """Generate Redis key for app count."""
        return f"apps:count:{tenant_id}"
    
    def record_execution(self, tenant_id: str, job_id: str) -> bool:
        """
        Record a new execution for the tenant.
        Returns True if successful, False otherwise.
        """
        try:
            key = self._get_execution_key(tenant_id)
            timestamp = timezone.now().timestamp()

            # Add execution to sorted set with timestamp as score
            self.redis.zadd(key, {f"{job_id}:{timestamp}": timestamp})

            # Set expiration to ensure cleanup
            self.redis.expire(key, self.EXECUTION_TTL + 3600)  # Extra hour for safety

            # Clean up old executions
            self._cleanup_old_executions(tenant_id)

            logger.info(f"Recorded execution for tenant {tenant_id}, job {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error recording execution: {e}")
            return False
    
    def get_execution_count(self, tenant_id: str, window_hours: int = 24) -> int:
        """
        Get the number of executions in the sliding window.
        """
        try:
            key = self._get_execution_key(tenant_id)
            now = timezone.now().timestamp()
            min_timestamp = now - (window_hours * 3600)

            # Count executions within the window
            count = self.redis.zcount(key, min_timestamp, now)

            logger.debug(f"Tenant {tenant_id} has {count} executions in last {window_hours} hours")
            return count or 0

        except Exception as e:
            logger.error(f"Error getting execution count: {e}")
            return 0
    
    def check_execution_quota(self, tenant_id: str, max_executions: int) -> Tuple[bool, int]:
        """
        Check if tenant can execute another job.
        Returns (can_execute, current_count).
        """
        current_count = self.get_execution_count(tenant_id)
        can_execute = current_count < max_executions

        if not can_execute:
            logger.warning(f"Tenant {tenant_id} reached execution quota: {current_count}/{max_executions}")

        return can_execute, current_count

    def check_and_record_execution_atomic(self, tenant_id: str, job_id: str, max_executions: int) -> Tuple[bool, int, Optional[str]]:
        """
        Atomically check quota and record execution if allowed.
        This prevents race conditions in concurrent requests.
        Returns (success, current_count, error_message).
        """
        try:
            key = self._get_execution_key(tenant_id)
            lock_key = f"lock:{key}"
            timestamp = timezone.now().timestamp()

            # Use Redis lock to ensure atomicity
            lock = self.cache.lock(lock_key, timeout=5)

            if not lock.acquire(blocking=True, blocking_timeout=5):
                logger.error(f"Failed to acquire lock for tenant {tenant_id}")
                return False, 0, "System is busy, please try again"

            try:
                # Clean up old executions first
                self._cleanup_old_executions(tenant_id)

                # Get current count within the lock
                current_count = self.get_execution_count(tenant_id)

                # Check if we can execute
                if current_count >= max_executions:
                    logger.warning(f"Tenant {tenant_id} quota exceeded: {current_count}/{max_executions}")
                    return False, current_count, f"Execution quota exceeded: {current_count}/{max_executions} executions in last 24h"

                # Record the execution
                self.redis.zadd(key, {f"{job_id}:{timestamp}": timestamp})
                self.redis.expire(key, self.EXECUTION_TTL + 3600)

                new_count = current_count + 1
                logger.info(f"Recorded execution for tenant {tenant_id}, job {job_id}. Count: {new_count}/{max_executions}")

                return True, new_count, None

            finally:
                lock.release()

        except Exception as e:
            logger.error(f"Error in atomic check and record: {e}")
            return False, 0, f"Internal error: {str(e)}"
    
    def _cleanup_old_executions(self, tenant_id: str):
        """
        Remove executions older than 24 hours.
        """
        try:
            key = self._get_execution_key(tenant_id)
            now = timezone.now().timestamp()
            min_timestamp = now - self.EXECUTION_TTL

            # Remove old executions
            removed = self.redis.zremrangebyscore(key, '-inf', min_timestamp)

            if removed:
                logger.debug(f"Cleaned up {removed} old executions for tenant {tenant_id}")

        except Exception as e:
            logger.error(f"Error cleaning up old executions: {e}")
    
    def get_execution_history(self, tenant_id: str, hours: int = 24) -> List[Dict]:
        """
        Get execution history for the tenant.
        """
        try:
            key = self._get_execution_key(tenant_id)
            now = timezone.now().timestamp()
            min_timestamp = now - (hours * 3600)

            # Get executions within the window
            executions = self.redis.zrangebyscore(
                key, min_timestamp, now, withscores=True
            )

            history = []
            for execution, timestamp in executions:
                # Handle bytes from Redis
                job_id_str = execution.decode('utf-8') if isinstance(execution, bytes) else execution
                job_id = job_id_str.split(':')[0] if ':' in job_id_str else job_id_str
                history.append({
                    'job_id': job_id,
                    'timestamp': timestamp,
                    'datetime': timezone.datetime.fromtimestamp(timestamp, tz=timezone.utc)
                })

            return history

        except Exception as e:
            logger.error(f"Error getting execution history: {e}")
            return []
    
    def update_app_count(self, tenant_id: str, count: int) -> bool:
        """
        Update the application count for a tenant.
        """
        try:
            key = self._get_app_count_key(tenant_id)
            self.cache.set(key, count, timeout=None)  # No expiration
            logger.info(f"Updated app count for tenant {tenant_id}: {count}")
            return True
        except Exception as e:
            logger.error(f"Error updating app count: {e}")
            return False
    
    def get_app_count(self, tenant_id: str) -> int:
        """
        Get the current application count for a tenant.
        """
        try:
            key = self._get_app_count_key(tenant_id)
            count = self.cache.get(key)
            return count if count is not None else 0
        except Exception as e:
            logger.error(f"Error getting app count: {e}")
            return 0
    
    def increment_app_count(self, tenant_id: str) -> int:
        """
        Increment and return the new application count.
        """
        try:
            key = self._get_app_count_key(tenant_id)
            return self.cache.incr(key)
        except Exception as e:
            logger.error(f"Error incrementing app count: {e}")
            return 0

    def check_and_increment_app_count_atomic(self, tenant_id: str, max_apps: int) -> Tuple[bool, int, Optional[str]]:
        """
        Atomically check max apps and increment count if allowed.
        This prevents race conditions when registering applications.
        Returns (success, current_count, error_message).
        """
        try:
            key = self._get_app_count_key(tenant_id)
            lock_key = f"lock:{key}"

            # Use Redis lock to ensure atomicity
            lock = self.cache.lock(lock_key, timeout=5)

            if not lock.acquire(blocking=True, blocking_timeout=5):
                logger.error(f"Failed to acquire lock for tenant {tenant_id} app count")
                return False, 0, "System is busy, please try again"

            try:
                # Get current count within the lock
                current_count = self.get_app_count(tenant_id)

                # Check if we can add another app
                if current_count >= max_apps:
                    logger.warning(f"Tenant {tenant_id} max apps reached: {current_count}/{max_apps}")
                    return False, current_count, f"Maximum number of applications reached: {current_count}/{max_apps}"

                # Increment the count
                # Set initial value if key doesn't exist, then increment
                if current_count == 0:
                    self.cache.set(key, 1, timeout=None)
                    new_count = 1
                else:
                    new_count = self.cache.incr(key)

                logger.info(f"Incremented app count for tenant {tenant_id}. Count: {new_count}/{max_apps}")

                return True, new_count, None

            finally:
                lock.release()

        except Exception as e:
            logger.error(f"Error in atomic check and increment app count: {e}")
            return False, 0, f"Internal error: {str(e)}"
    
    def decrement_app_count(self, tenant_id: str) -> int:
        """
        Decrement and return the new application count.
        """
        try:
            key = self._get_app_count_key(tenant_id)
            return self.cache.decr(key)
        except Exception as e:
            logger.error(f"Error decrementing app count: {e}")
            return 0
    
    def reset_tenant_data(self, tenant_id: str):
        """
        Reset all cached data for a tenant.
        """
        try:
            # Clear executions
            exec_key = self._get_execution_key(tenant_id)
            self.cache.delete(exec_key)
            
            # Clear app count
            app_key = self._get_app_count_key(tenant_id)
            self.cache.delete(app_key)
            
            logger.info(f"Reset all cached data for tenant {tenant_id}")
            
        except Exception as e:
            logger.error(f"Error resetting tenant data: {e}")
    
    def get_quota_status(self, tenant_id: str, max_executions: int, max_apps: int) -> Dict:
        """
        Get comprehensive quota status for a tenant.
        """
        execution_count = self.get_execution_count(tenant_id)
        app_count = self.get_app_count(tenant_id)
        
        return {
            'tenant_id': tenant_id,
            'executions': {
                'current': execution_count,
                'max': max_executions,
                'remaining': max(0, max_executions - execution_count),
                'percentage_used': (execution_count / max_executions * 100) if max_executions > 0 else 0
            },
            'applications': {
                'current': app_count,
                'max': max_apps,
                'remaining': max(0, max_apps - app_count),
                'percentage_used': (app_count / max_apps * 100) if max_apps > 0 else 0
            },
            'timestamp': timezone.now()
        }


# Global instance
quota_service = QuotaService()
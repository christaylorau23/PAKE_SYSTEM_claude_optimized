"""RateLimitController - Manages API rate limiting across all platforms

Implements intelligent rate limiting, cost optimization, and graceful degradation.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RateLimit:
    """Rate limit configuration for an API"""

    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    cost_per_request: float = 0.0
    burst_allowance: int = 0


@dataclass
class RequestHistory:
    """Track request history for rate limiting"""

    timestamps: deque = field(default_factory=deque)
    costs: deque = field(default_factory=deque)
    total_requests: int = 0
    total_cost: float = 0.0


class RateLimitController:
    """Advanced rate limiting controller with cost optimization

    Features:
    - Per-API rate limiting
    - Cost tracking and budgeting
    - Burst allowance handling
    - Intelligent backoff strategies
    - Priority-based request queuing
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Rate limit configurations
        self.rate_limits: dict[str, RateLimit] = {
            "google_trends": RateLimit(
                requests_per_minute=10,
                requests_per_hour=500,
                requests_per_day=5000,
                cost_per_request=0.0,  # Free API
                burst_allowance=5,
            ),
            "youtube": RateLimit(
                requests_per_minute=100,
                requests_per_hour=1000,
                requests_per_day=10000,
                cost_per_request=0.001,  # $0.001 per request
                burst_allowance=20,
            ),
            "twitter": RateLimit(
                requests_per_minute=50,
                requests_per_hour=1500,
                requests_per_day=10000,
                cost_per_request=0.005,  # $0.005 per request
                burst_allowance=10,
            ),
            "tiktok": RateLimit(
                requests_per_minute=20,
                requests_per_hour=800,
                requests_per_day=5000,
                cost_per_request=0.01,  # $0.01 per request
                burst_allowance=5,
            ),
        }

        # Request tracking
        self.request_history: dict[str, RequestHistory] = defaultdict(RequestHistory)

        # Cost budgeting
        self.daily_budget = 100.0  # $100 daily budget
        self.hourly_budget = 10.0  # $10 hourly budget

        # Priority queues for request management
        self.request_queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.processing_requests = set()

    async def can_make_request(self, api_name: str, priority: int = 1) -> bool:
        """Check if a request can be made considering rate limits and budget

        Args:
            api_name: Name of the API
            priority: Priority level (1=highest, 5=lowest)

        Returns:
            bool: True if request can be made
        """
        if api_name not in self.rate_limits:
            self.logger.warning(f"Unknown API: {api_name}")
            return False

        rate_limit = self.rate_limits[api_name]
        history = self.request_history[api_name]

        # Check rate limits
        now = time.time()
        if not self._check_rate_limits(history, rate_limit, now):
            return False

        # Check budget constraints
        if not self._check_budget_constraints(rate_limit.cost_per_request):
            return False

        return True

    def _check_rate_limits(
        self,
        history: RequestHistory,
        rate_limit: RateLimit,
        now: float,
    ) -> bool:
        """Check if rate limits are satisfied"""
        # Clean old timestamps
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400

        # Remove old entries
        while history.timestamps and history.timestamps[0] < day_ago:
            history.timestamps.popleft()
            if history.costs:
                history.costs.popleft()

        # Count requests in different time windows
        minute_count = sum(1 for ts in history.timestamps if ts > minute_ago)
        hour_count = sum(1 for ts in history.timestamps if ts > hour_ago)
        day_count = len(history.timestamps)

        # Check limits
        if minute_count >= rate_limit.requests_per_minute:
            return False
        if hour_count >= rate_limit.requests_per_hour:
            return False
        if day_count >= rate_limit.requests_per_day:
            return False

        return True

    def _check_budget_constraints(self, cost_per_request: float) -> bool:
        """Check if request fits within budget constraints"""
        if cost_per_request == 0.0:
            return True

        # Calculate current spending
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400

        hourly_spending = 0.0
        daily_spending = 0.0

        for api_name, history in self.request_history.items():
            for i, timestamp in enumerate(history.timestamps):
                if timestamp > day_ago:
                    if i < len(history.costs):
                        cost = history.costs[i]
                        daily_spending += cost
                        if timestamp > hour_ago:
                            hourly_spending += cost

        # Check if new request would exceed budget
        if hourly_spending + cost_per_request > self.hourly_budget:
            self.logger.warning(
                f"Request would exceed hourly budget: ${hourly_spending:.2f} + ${
                    cost_per_request:.2f} > ${self.hourly_budget:.2f}",
            )
            return False

        if daily_spending + cost_per_request > self.daily_budget:
            self.logger.warning(
                f"Request would exceed daily budget: ${daily_spending:.2f} + ${
                    cost_per_request:.2f} > ${self.daily_budget:.2f}",
            )
            return False

        return True

    async def record_request(self, api_name: str, success: bool = True) -> None:
        """Record a completed request for tracking"""
        if api_name not in self.rate_limits:
            return

        rate_limit = self.rate_limits[api_name]
        history = self.request_history[api_name]

        now = time.time()
        history.timestamps.append(now)
        history.costs.append(rate_limit.cost_per_request)
        history.total_requests += 1
        history.total_cost += rate_limit.cost_per_request

        if success:
            self.logger.debug(f"Recorded successful request for {api_name}")
        else:
            self.logger.warning(f"Recorded failed request for {api_name}")

    async def get_remaining_quota(self, api_name: str) -> dict[str, int]:
        """Get remaining quota for an API"""
        if api_name not in self.rate_limits:
            return {}

        rate_limit = self.rate_limits[api_name]
        history = self.request_history[api_name]

        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400

        minute_count = sum(1 for ts in history.timestamps if ts > minute_ago)
        hour_count = sum(1 for ts in history.timestamps if ts > hour_ago)
        day_count = sum(1 for ts in history.timestamps if ts > day_ago)

        return {
            "minute_remaining": max(0, rate_limit.requests_per_minute - minute_count),
            "hour_remaining": max(0, rate_limit.requests_per_hour - hour_count),
            "day_remaining": max(0, rate_limit.requests_per_day - day_count),
        }

    async def get_cost_summary(self) -> dict[str, Any]:
        """Get cost summary across all APIs"""
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400

        hourly_costs = {}
        daily_costs = {}
        total_hourly = 0.0
        total_daily = 0.0

        for api_name, history in self.request_history.items():
            api_hourly = 0.0
            api_daily = 0.0

            for i, timestamp in enumerate(history.timestamps):
                if timestamp > day_ago and i < len(history.costs):
                    cost = history.costs[i]
                    api_daily += cost
                    if timestamp > hour_ago:
                        api_hourly += cost

            hourly_costs[api_name] = api_hourly
            daily_costs[api_name] = api_daily
            total_hourly += api_hourly
            total_daily += api_daily

        return {
            "hourly_costs": hourly_costs,
            "daily_costs": daily_costs,
            "total_hourly": total_hourly,
            "total_daily": total_daily,
            "hourly_budget": self.hourly_budget,
            "daily_budget": self.daily_budget,
            "hourly_budget_remaining": max(0, self.hourly_budget - total_hourly),
            "daily_budget_remaining": max(0, self.daily_budget - total_daily),
            "hourly_budget_utilization": (total_hourly / self.hourly_budget) * 100,
            "daily_budget_utilization": (total_daily / self.daily_budget) * 100,
        }

    async def calculate_backoff_time(self, api_name: str) -> float:
        """Calculate intelligent backoff time for rate-limited API"""
        if api_name not in self.rate_limits:
            return 60.0

        rate_limit = self.rate_limits[api_name]
        history = self.request_history[api_name]

        now = time.time()
        minute_ago = now - 60

        # Count recent requests
        recent_requests = sum(1 for ts in history.timestamps if ts > minute_ago)

        if recent_requests >= rate_limit.requests_per_minute:
            # Calculate time to wait for oldest request to expire
            oldest_in_window = min(ts for ts in history.timestamps if ts > minute_ago)
            return max(1.0, 60.0 - (now - oldest_in_window))

        return 0.0

    async def optimize_request_scheduling(
        self,
        api_requests: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Optimize request scheduling based on rate limits and costs

        Args:
            api_requests: List of request specifications with 'api_name', 'priority', etc.

        Returns:
            List of optimized request schedule
        """
        # Sort by priority and cost efficiency
        sorted_requests = sorted(
            api_requests,
            key=lambda x: (
                x.get("priority", 3),  # Lower number = higher priority
                -self.rate_limits.get(
                    x["api_name"],
                    RateLimit(1, 1, 1),
                ).cost_per_request,  # Lower cost first
            ),
        )

        optimized_schedule = []
        for request in sorted_requests:
            api_name = request["api_name"]
            if await self.can_make_request(api_name, request.get("priority", 3)):
                optimized_schedule.append(request)
            else:
                # Calculate when this request could be made
                backoff_time = await self.calculate_backoff_time(api_name)
                request["scheduled_time"] = time.time() + backoff_time
                optimized_schedule.append(request)

        return optimized_schedule

    def get_rate_limit_status(self) -> dict[str, Any]:
        """Get comprehensive rate limit status"""
        status = {}

        for api_name, rate_limit in self.rate_limits.items():
            history = self.request_history[api_name]
            quota = asyncio.create_task(self.get_remaining_quota(api_name))

            status[api_name] = {
                "rate_limit": {
                    "requests_per_minute": rate_limit.requests_per_minute,
                    "requests_per_hour": rate_limit.requests_per_hour,
                    "requests_per_day": rate_limit.requests_per_day,
                    "cost_per_request": rate_limit.cost_per_request,
                },
                "usage": {
                    "total_requests": history.total_requests,
                    "total_cost": history.total_cost,
                },
                "health": self._calculate_api_health(api_name),
            }

        return status

    def _calculate_api_health(self, api_name: str) -> float:
        """Calculate health score for API (0.0 to 1.0)"""
        if api_name not in self.request_history:
            return 1.0

        history = self.request_history[api_name]
        rate_limit = self.rate_limits[api_name]

        # Calculate utilization
        now = time.time()
        hour_ago = now - 3600
        hour_requests = sum(1 for ts in history.timestamps if ts > hour_ago)
        hour_utilization = hour_requests / rate_limit.requests_per_hour

        # Health decreases as utilization approaches limits
        if hour_utilization < 0.5:
            return 1.0
        if hour_utilization < 0.8:
            return 0.8
        if hour_utilization < 0.95:
            return 0.5
        return 0.2

    async def set_budget(self, hourly_budget: float, daily_budget: float):
        """Update budget constraints"""
        self.hourly_budget = hourly_budget
        self.daily_budget = daily_budget
        self.logger.info(
            f"Updated budgets: hourly=${hourly_budget:.2f}, daily=${daily_budget:.2f}",
        )

    async def emergency_throttle(self, api_name: str, reduction_factor: float = 0.5):
        """Emergency throttle for specific API"""
        if api_name in self.rate_limits:
            rate_limit = self.rate_limits[api_name]
            self.rate_limits[api_name] = RateLimit(
                requests_per_minute=int(
                    rate_limit.requests_per_minute * reduction_factor,
                ),
                requests_per_hour=int(rate_limit.requests_per_hour * reduction_factor),
                requests_per_day=int(rate_limit.requests_per_day * reduction_factor),
                cost_per_request=rate_limit.cost_per_request,
                burst_allowance=int(rate_limit.burst_allowance * reduction_factor),
            )
            self.logger.warning(
                f"Emergency throttle applied to {api_name}: {reduction_factor:.1%} reduction",
            )

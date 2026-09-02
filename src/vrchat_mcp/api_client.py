"""
VRChat REST API Client Wrapper: SOTA Industrial v14.1.0

Handles authentication, session persistence, 2FA handshakes, and 60s caching
to comply with VRChat API policies while providing high-fidelity metadata.
"""

import logging
from typing import Any

import vrchatapi
from cachetools import TTLCache
from vrchatapi.api import authentication_api, economy_api, friends_api, notifications_api, users_api, worlds_api
from vrchatapi.exceptions import UnauthorizedException
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode

logger = logging.getLogger(__name__)


class VRChatAPIClient:
    def __init__(self, username: str = "", password: str = ""):
        self.username = username
        self.password = password
        self.configuration = vrchatapi.Configuration(
            username=username,
            password=password,
        )
        self.api_client = vrchatapi.ApiClient(self.configuration)
        self.api_client.user_agent = "VRChat-MCP-SOTA/14.1.0 (industrial-compliance)"

        # APIs
        self.auth_api = authentication_api.AuthenticationApi(self.api_client)
        self.worlds_api = worlds_api.WorldsApi(self.api_client)
        self.economy_api = economy_api.EconomyApi(self.api_client)
        # Added 2026-09-03 - vrchatapi (already a dependency) exposes 18 API classes; this
        # wrapper only used 3 of them. Friends/users/notifications is the most directly
        # useful next slice, not the whole surface (groups/instances/avatars/etc. remain
        # unwired - see CHANGELOG for what's still open).
        self.friends_api = friends_api.FriendsApi(self.api_client)
        self.users_api = users_api.UsersApi(self.api_client)
        self.notifications_api = notifications_api.NotificationsApi(self.api_client)

        # State
        self.current_user = None
        self.needs_2fa = False
        self.two_factor_type = None  # "email" or "totp"

        # Cache (60s TTL as per VRChat policy)
        self.world_cache = TTLCache(maxsize=100, ttl=60)
        self.economy_cache = TTLCache(maxsize=10, ttl=60)
        self.user_cache = TTLCache(maxsize=200, ttl=60)
        self.friends_cache = TTLCache(maxsize=1, ttl=60)

    async def login(self) -> dict[str, Any]:
        """Perform login handshake."""
        try:
            # Login call is blocking in the SDK, so we run in executor if needed
            # but for simplicity in this industrial wrapper we coordinate state
            self.current_user = self.auth_api.get_current_user()
            logger.info(f"Successfully logged into VRChat as: {self.current_user.display_name}")
            self.needs_2fa = False
            return {"status": "success", "user": self.current_user.to_dict()}

        except UnauthorizedException as e:
            if e.status == 200:
                if "Email 2 Factor Authentication" in e.reason:
                    self.needs_2fa = True
                    self.two_factor_type = "email"
                    logger.warning("VRChat login requires Email 2FA code.")
                elif "2 Factor Authentication" in e.reason:
                    self.needs_2fa = True
                    self.two_factor_type = "totp"
                    logger.warning("VRChat login requires TOTP 2FA code.")
                return {"status": "needs_2fa", "type": self.two_factor_type}
            raise e

    async def verify_2fa(self, code: str) -> bool:
        """Submit 2FA code."""
        try:
            if self.two_factor_type == "email":
                self.auth_api.verify2_fa_email_code(two_factor_email_code=TwoFactorEmailCode(code))
            else:
                self.auth_api.verify2_fa(two_factor_auth_code=TwoFactorAuthCode(code))

            self.current_user = self.auth_api.get_current_user()
            self.needs_2fa = False
            logger.info(f"2FA Verified. Logged in as: {self.current_user.display_name}")
            return True
        except Exception as e:
            logger.error(f"2FA Verification failed: {e}")
            return False

    async def get_world_info(self, world_id: str) -> dict[str, Any]:
        """Fetch world metadata with 60s caching."""
        if world_id in self.world_cache:
            return self.world_cache[world_id]

        world = self.worlds_api.get_world(world_id)
        data = world.to_dict()
        self.world_cache[world_id] = data
        return data

    async def get_economy_info(self) -> dict[str, Any]:
        """Fetch the real VRChat Credit balance for the logged-in user, with 60s caching.

        Fixed 2026-09-03: this previously returned a hardcoded {"credits": 5000, "status":
        "active"} regardless of the actual account - a fabricated-looking real value, not an
        honest placeholder. EconomyApi.get_balance() has been a real method on the installed
        vrchatapi SDK the whole time; nothing blocked wiring it up.
        """
        cache_key = "current_balance"
        if cache_key in self.economy_cache:
            return self.economy_cache[cache_key]

        if not self.current_user:
            return {"error": "Not logged in - call login() first."}

        try:
            balance = self.economy_api.get_balance(self.current_user.id)
            data = balance.to_dict()
            self.economy_cache[cache_key] = data
            return data
        except Exception as e:
            logger.error(f"Failed to fetch economy balance: {e}")
            return {"error": str(e)}

    async def get_products_and_subscriptions(self) -> dict[str, Any]:
        """Fetch real owned product purchases + active subscriptions. Fixed 2026-09-03 -
        manage_economy's "products" operation previously returned a hardcoded empty
        placeholder ({"products": [], "subscriptions": []}) unconditionally, same fake-data
        pattern as the balance fix above."""
        if not self.current_user:
            return {"error": "Not logged in - call login() first."}
        try:
            purchases = self.economy_api.get_product_purchases(self.current_user.id)
            subscriptions = self.economy_api.get_current_subscriptions()
            return {
                "products": [p.to_dict() for p in purchases],
                "subscriptions": [s.to_dict() for s in subscriptions],
            }
        except Exception as e:
            logger.error(f"Failed to fetch products/subscriptions: {e}")
            return {"error": str(e)}

    async def get_friends(self, offline: bool = False) -> dict[str, Any]:
        """List friends, with 60s caching. offline=True lists offline friends instead of
        online/active ones (VRChat's own API split, not a client-side filter)."""
        cache_key = f"friends_{offline}"
        if cache_key in self.friends_cache:
            return self.friends_cache[cache_key]
        try:
            friends = self.friends_api.get_friends(offline=offline)
            data = {"friends": [f.to_dict() for f in friends], "count": len(friends)}
            self.friends_cache[cache_key] = data
            return data
        except Exception as e:
            logger.error(f"Failed to fetch friends: {e}")
            return {"error": str(e)}

    async def get_friend_status(self, user_id: str) -> dict[str, Any]:
        """Check friendship/request status with a specific user (not cached - status can
        change quickly, e.g. right after sending a request)."""
        try:
            status = self.friends_api.get_friend_status(user_id)
            return status.to_dict()
        except Exception as e:
            logger.error(f"Failed to fetch friend status for {user_id}: {e}")
            return {"error": str(e)}

    async def send_friend_request(self, user_id: str) -> dict[str, Any]:
        try:
            result = self.friends_api.friend(user_id)
            return result.to_dict()
        except Exception as e:
            logger.error(f"Failed to send friend request to {user_id}: {e}")
            return {"error": str(e)}

    async def unfriend(self, user_id: str) -> dict[str, Any]:
        try:
            self.friends_api.unfriend(user_id)
            return {"status": "success", "user_id": user_id}
        except Exception as e:
            logger.error(f"Failed to unfriend {user_id}: {e}")
            return {"error": str(e)}

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Fetch a user's public profile by ID, with 60s caching."""
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        try:
            user = self.users_api.get_user(user_id)
            data = user.to_dict()
            self.user_cache[user_id] = data
            return data
        except Exception as e:
            logger.error(f"Failed to fetch user {user_id}: {e}")
            return {"error": str(e)}

    async def get_user_by_name(self, username: str) -> dict[str, Any]:
        try:
            user = self.users_api.get_user_by_name(username)
            return user.to_dict()
        except Exception as e:
            logger.error(f"Failed to fetch user by name {username}: {e}")
            return {"error": str(e)}

    async def search_users(self, query: str, limit: int = 20) -> dict[str, Any]:
        try:
            results = self.users_api.search_users(search=query, n=limit)
            return {"query": query, "results": [u.to_dict() for u in results], "count": len(results)}
        except Exception as e:
            logger.error(f"Failed to search users for {query!r}: {e}")
            return {"error": str(e)}

    async def get_notifications(self, notif_type: str | None = None) -> dict[str, Any]:
        """List recent VRChat account notifications (friend requests, invites, etc.) via
        REST - separate from PipelineClient's real-time websocket stream of the same kind of
        events; this is a point-in-time REST snapshot, not a live feed."""
        try:
            kwargs = {"type": notif_type} if notif_type else {}
            notifications = self.notifications_api.get_notifications(**kwargs)
            return {"notifications": [n.to_dict() for n in notifications], "count": len(notifications)}
        except Exception as e:
            logger.error(f"Failed to fetch notifications: {e}")
            return {"error": str(e)}

    async def accept_friend_request(self, notification_id: str) -> dict[str, Any]:
        try:
            self.notifications_api.accept_friend_request(notification_id)
            return {"status": "success", "notification_id": notification_id}
        except Exception as e:
            logger.error(f"Failed to accept friend request {notification_id}: {e}")
            return {"error": str(e)}

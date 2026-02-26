class NullWishlistCache:
    async def get_list(self, user_id: int, limit: int, offset: int):
        return None
    async def set_list(self, user_id: int, limit: int, offset: int, data: list):
        return False
    async def get_item(self, slug: str, role: str):
        return None
    async def set_item(self, slug: str, role: str, data: dict):
        return False
    async def invalidate_wishlist(self, slug: str):
        pass
    async def invalidate_lists(self, user_id: int):
        pass
    async def ping(self):
        return True
    async def get_stats(self):
        return {}

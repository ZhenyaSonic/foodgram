from django.contrib import admin

from .models import (
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Tag,
)
from users.models import User


admin.site.register(User)
admin.site.register(Recipe)
admin.site.register(Ingredient)
admin.site.register(Tag)
admin.site.register(Favorite)
admin.site.register(ShoppingCart)

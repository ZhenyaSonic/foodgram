# from users.models import Subscription
import hashlib

SHORT_LINK_LENGTH = 6


def is_subscribed(user, author):
    if user.is_anonymous:
        return False
    return user.subscriptions.filter(author=author).exists()


def generate_short_link_code(recipe_id):
    return hashlib.md5(str(recipe_id).encode()).hexdigest()[:SHORT_LINK_LENGTH]

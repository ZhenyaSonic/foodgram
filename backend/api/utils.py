# from users.models import Subscription

def is_subscribed(user, author):
    if user.is_anonymous:
        return False
    return user.subscriptions.filter(author=author).exists()

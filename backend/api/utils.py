from users.models import Subscription


def is_subscribed(user, author):
    if user.is_anonymous:
        return False
    return Subscription.objects.filter(user=user, author=author).exists()

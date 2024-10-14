from django.contrib.auth.models import AbstractUser
from django.db.models.constraints import UniqueConstraint
from django.db import models


class User(AbstractUser):

    email = models.EmailField(
        'Почта',
        unique=True,
        max_length=254
    )
    first_name = models.CharField(
        'Имя',
        max_length=150
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=150
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.username


class Subscription(models.Model):

    user = models.ForeignKey(
        User,
        related_name='subscriptions',
        on_delete=models.CASCADE,
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        related_name='subscribers',
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            UniqueConstraint(
                fields=('user', 'author'),
                name='unique_subscription'
            )
        ]

    def __str__(self):
        return f'{self.user}'

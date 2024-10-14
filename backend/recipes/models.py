from django.db import models
from django.db.models.constraints import UniqueConstraint
from django.core.validators import MaxValueValidator, MinValueValidator

from users.models import User


class Tag(models.Model):

    name = models.CharField(
        'Тег',
        max_length=200,
    )
    slug = models.SlugField(
        'Уникальный слаг',
        max_length=200,
        unique=True,
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):

    name = models.CharField(
        'Ингредиент',
        max_length=200,
    )
    measurement_unit = models.CharField(
        'Единицы измерения',
        max_length=200,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор',
    )
    name = models.CharField(
        'рецепты',
        max_length=200,
        db_index=True,
    )
    image = models.ImageField(
        upload_to='recipes/'
    )
    text = models.TextField(
        'Описание',
        max_length=300,
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги',
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления',
        validators=[MinValueValidator(1), MaxValueValidator(999)]
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Ингредиент',
    )
    amount = models.PositiveIntegerField(
        'Количество',
        validators=[MinValueValidator(1), MaxValueValidator(999)]
    )

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        constraints = [
            UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.ingredient.name}'


class ShoppingCart(models.Model):

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Рецепт',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart'
    )

    class Meta:
        verbose_name = 'Cписок покупок'
        verbose_name_plural = 'Cписки покупок'
        constraints = [
            UniqueConstraint(
                fields=('recipe', 'author'),
                name='unique_shoppingcart'
            )
        ]

    def __str__(self):
        return f'{self.recipe.name}'


class Favorite(models.Model):

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorite',
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'
        constraints = [
            UniqueConstraint(
                fields=('recipe', 'author'),
                name='unique_favorite'
            )
        ]

    def __str__(self):
        return f'{self.recipe.name}'

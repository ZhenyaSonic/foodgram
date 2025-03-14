import base64

from rest_framework import serializers
from djoser.serializers import UserCreateSerializer, UserSerializer
from django.core.files.base import ContentFile

from recipes.models import (
    Ingredient,
    RecipeIngredient,
    Recipe,
    Tag,
)
from users.models import User
from .utils import is_subscribed
from .fields import Base64ImageField
from foodgram.settings import MIN_VALUE, MAX_VALUE


class CustomUserSerializer(UserSerializer):

    avatar = Base64ImageField(required=False)
    is_subscribed = serializers.SerializerMethodField(
        method_name='get_is_subscribed'
    )

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
        )

    def update(self, instance, validated_data):

        avatar_data = validated_data.pop('avatar', None)
        if avatar_data:
            format, imgstr = avatar_data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'avatar.{ext}')
            instance.avatar.save(f'avatar.{ext}', data, save=True)
        if not avatar_data:
            raise serializers.ValidationError('Добавьте поле аватар.')

        return super().update(instance, validated_data)

    def delete_avatar(self):
        user = self.instance
        user.avatar.delete()
        user.save()

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return is_subscribed(request.user, obj)


class CustomUserCreateSerializer(UserCreateSerializer):

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )


class SubscriptionSerializer(serializers.ModelSerializer):

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )
        read_only_fields = ('email', 'username', 'first_name', 'last_name')

    def validate(self, data):
        author = data.get('author')
        user = data.get('user')
        if author == user:
            raise serializers.ValidationError(
                'Нельзя подписаться на самаого себя.'
            )
        return data

    def get_is_subscribed(self, obj):
        request = self.context['request']
        return is_subscribed(request.user, obj)

    def get_recipes(self, obj):
        request = self.context['request']
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[: int(limit)]
        serializer = ShoppingCartRecipeSerializer(
            recipes,
            many=True,
            read_only=True
        )
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientsSerializer(serializers.ModelSerializer):

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeGetSerializer(serializers.ModelSerializer):

    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientsSerializer(
        many=True,
        source='recipe_ingredients'
    )
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'image',
            'text', 'cooking_time', 'is_favorited', 'is_in_shopping_cart'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.favorite.filter(author=user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return user.shopping_cart.filter(recipe=obj).exists()
        return False


class IngredientsAmountSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        error_messages={
            'min_value': 'Количество ингредиента должно быть не менее 1.',
            'max_value': 'Количество ингредиента не может превышать 32000.'
        }
    )

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class CreateRecipeSerializer(serializers.ModelSerializer):

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientsAmountSerializer(many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        error_messages={
            'min_value': 'Время приготовления должно быть не менее 1 минуты.',
            'max_value': 'Время приготовления не может превышать 32000 минут.'
        }
    )

    class Meta:
        model = Recipe
        fields = (
            'tags', 'author', 'ingredients', 'name',
            'image', 'text', 'cooking_time'
        )

    def validate_ingredients_and_tags(self, ingredients, tags):
        if not ingredients:
            raise serializers.ValidationError('Рецепт без ингредиентов.')

        if not tags:
            raise serializers.ValidationError('Рецепт без Тегов.')

        ingredient_ids = set()
        tag_names = set()

        # Объединенный цикл для проверки ингредиентов и тегов
        for ingredient in ingredients:
            ingredient_id = ingredient['id']

            # Проверка существования ингредиента
            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(
                    f'Ингредиент {ingredient_id} не существует.'
                )

            # Проверка на дубликаты ингредиентов
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    f'Ингредиент с ID {ingredient_id} уже добавлен.'
                )
            ingredient_ids.add(ingredient_id)

        for tag in tags:
            # Проверка существования тега
            if not Tag.objects.filter(name=tag).exists():
                raise serializers.ValidationError(
                    f'Данного тэга {tag} нет в списке доступных.'
                )

            # Проверка на дубликаты тегов
            if tag in tag_names:
                raise serializers.ValidationError(
                    'Повторяющих тегов не должно быть.'
                )
            tag_names.add(tag)

        return ingredients, tags

    def add_recipe_ingredients(self, ingredients, recipe):
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.add_recipe_ingredients(ingredients_data, recipe)

        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)

        instance = super().update(instance, validated_data)

        instance.ingredients.clear()
        self.add_recipe_ingredients(ingredients_data, instance)

        instance.tags.clear()
        instance.tags.set(tags)

        return instance

    def to_representation(self, instance):
        return RecipeGetSerializer(
            instance, context={'request': self.context.get('request')}
        ).data


class ShoppingCartRecipeSerializer(serializers.ModelSerializer):

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

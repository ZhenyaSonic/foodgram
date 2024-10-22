import csv
import hashlib

from django.urls import reverse
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from djoser.views import UserViewSet

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import AdminOrAuthorOrReadOnly
from .utils import generate_short_link_code
from .serializers import (
    CreateRecipeSerializer,
    IngredientSerializer,
    RecipeGetSerializer,
    ShoppingCartRecipeSerializer,
    TagSerializer,
    CustomUserSerializer,
    SubscriptionSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    RecipeIngredient,
    Recipe,
    ShoppingCart,
    Tag
)
from users.models import User, Subscription


class CustomUserViewSet(UserViewSet):

    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action == 'me':
            return IsAuthenticated(),
        return super().get_permissions()

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def update_avatar(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user)

        if request.method == 'PUT':
            serializer.update(user, request.data)
            avatar_url = request.build_absolute_uri(user.avatar.url)
            return Response({'avatar': avatar_url}, status=status.HTTP_200_OK)

        serializer.delete_avatar()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        user = request.user
        subscribed_users = user.subscriptions.all()
        users = User.objects.filter(
            id__in=subscribed_users.values_list('author', flat=True)
        )
        page = self.paginate_queryset(users)
        serializer = SubscriptionSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, id=None):
        author = self.get_object()
        user = request.user

        if request.method == 'POST':
            if author == user:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            if user.subscriptions.filter(author=author).exists():
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=user, author=author)
            serializer = SubscriptionSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        try:
            subscription = Subscription.objects.get(
                user=user,
                author=author
            )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Subscription.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    search_fields = ['name']


class TagViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = (DjangoFilterBackend,)


class RecipeViewSet(viewsets.ModelViewSet):

    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = (AdminOrAuthorOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeGetSerializer
        return CreateRecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def add_recipe(self, model, user, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        if model.objects.filter(recipe=recipe, author=user).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        model.objects.create(recipe=recipe, author=user)
        serializer = ShoppingCartRecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_recipe(self, model, user, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        obj = model.objects.filter(recipe=recipe, author=user).first()
        if obj:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        permission_classes=(IsAuthenticated,),
        methods=('post', 'delete'),
        url_path='shopping_cart'
    )
    def shopping_cart(self, request, pk):
        author = self.request.user
        if request.method == 'POST':
            return self.add_recipe(ShoppingCart, author, pk)

        return self.delete_recipe(ShoppingCart, author, pk)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
        methods=['get'],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        user = request.user

        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__author=user
        ).values('ingredient__name', 'ingredient__measurement_unit').annotate(
            ingredients_amount=Sum('amount')
        )

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(['Ingredient', 'Amount'])

        for ingredient in ingredients:
            writer.writerow([
                ingredient['ingredient__name'],
                ingredient['ingredient__measurement_unit'],
                ingredient['ingredients_amount']
            ]
            )

        return response

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        short_link_code = generate_short_link_code(recipe.id)
        short_link = request.build_absolute_uri(
            reverse('short_link', kwargs={'pk': short_link_code})
        )

        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        permission_classes=(IsAuthenticated,),
        methods=('post', 'delete'),
        url_path='favorite'
    )
    def favorite(self, request, pk):
        author = self.request.user
        if request.method == 'POST':
            return self.add_recipe(Favorite, author, pk)

        return self.delete_recipe(Favorite, author, pk)


def short_link(request, pk):
    recipes = Recipe.objects.all()

    for recipe in recipes:
        id_recipe = generate_short_link_code(recipe.id)
        if id_recipe == pk:
            return redirect(f'/recipes/{recipe.id}/')

    return HttpResponse(
        f'Не существует рецепта с коротким кодом {pk}',
        status=404
    )

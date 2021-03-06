import uuid

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.mixins import ListModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from apps.account.models import User
from apps.account.serializers import UserSerializer
from common.drf.mixins import CacheMixin
from common.drf.pagination import StandardResultsSetPagination

from .models import Story, Tag
from .serializers import StoryCreateUpdateSerializer, StoryRetrieveSerializer, TagSerializer


class StoryViewSet(CacheMixin, ModelViewSet):
    """ Provide all methods for manage Story. """

    queryset = Story.objects.all()
    lookup_field = 'slug'
    filter_backends = (OrderingFilter,)
    ordering_fields = ('created',)
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        """Instantiates and returns the list of permissions that this view requires. """
        if self.action in ['retrieve', 'list', 'add_view']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """ Customize the queryset according to the current user. """
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset
        return queryset.filter(published=True)

    def get_serializer_class(self):
        """ Return a dedicated serializer according to the HTTP verb. """
        if self.action not in ['retrieve', 'list']:
            return StoryCreateUpdateSerializer
        return StoryRetrieveSerializer

    @action(detail=True, methods=['post'], url_name='add_view')
    def add_view(self, request, slug=None):
        """ Increments the recipe views. """
        story = self.get_object()
        story.views += 1
        story.save()
        return Response(status=status.HTTP_200_OK)


class AuthorViewSet(ListModelMixin, GenericViewSet):
    """ Provide a list view for Author. """

    queryset = User.objects.filter(is_staff=True)
    serializer_class = UserSerializer


class TagViewSet(CacheMixin, ListModelMixin, GenericViewSet):
    """ Provide a list view for Tag. """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class UploadImageViewSet(ViewSet):
    """ Provide a way to upload image. """
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser]

    def create(self, request, format=None):
        """ Upload an image and return the URL. """
        file = request.FILES.get('file')

        # Check if file is a valid image
        f = forms.ImageField()
        try:
            f.clean(file)
        except ValidationError as err:
            return Response({'detail': err}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        # Generate filename
        extension = file.name.split('.')[-1]
        filename = f'{uuid.uuid4()}.{extension}'

        # Save image in media directory
        path = default_storage.save(f'uploads/{filename}', file)

        # Build URL
        image_url = request.build_absolute_uri(default_storage.url(path))
        return Response({'image_url': image_url}, status=status.HTTP_200_OK)

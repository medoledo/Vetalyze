from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OwnerViewSet, PetTypeViewSet, SocialMediaViewSet

router = DefaultRouter()
router.register(r'clients', OwnerViewSet, basename='owner')
router.register(r'pet-types', PetTypeViewSet)
router.register(r'social-media', SocialMediaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
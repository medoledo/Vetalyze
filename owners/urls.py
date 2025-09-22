from django.urls import path, include
from .views import (
    OwnerListCreateView,
    OwnerDetailView,
    PetTypeListCreateView,
    PetTypeDetailView,
    MarketingChannelListCreateView,
    MarketingChannelDetailView,
)

urlpatterns = [
    path('clients/', OwnerListCreateView.as_view(), name='owner-list-create'),
    path('clients/<int:pk>/', OwnerDetailView.as_view(), name='owner-detail'),

    path('pet-types/', PetTypeListCreateView.as_view(), name='pettype-list-create'),
    path('pet-types/<int:pk>/', PetTypeDetailView.as_view(), name='pettype-detail'),

    path('marketing-channels/', MarketingChannelListCreateView.as_view(), name='marketingchannel-list-create'),
    path('marketing-channels/<int:pk>/', MarketingChannelDetailView.as_view(), name='marketingchannel-detail'),
]
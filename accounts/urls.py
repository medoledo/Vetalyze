from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import (
    CustomTokenObtainPairView, 
    public_key_view,
    ClinicOwnerProfileViewSet, 
    DoctorProfileViewSet, 
    ReceptionProfileViewSet,
    SubscriptionTypeViewSet,
    PaymentMethodViewSet
)

router = DefaultRouter()
router.register(r'clinic-owner-profiles', ClinicOwnerProfileViewSet)
router.register(r'doctor-profiles', DoctorProfileViewSet)
router.register(r'reception-profiles', ReceptionProfileViewSet)
router.register(r'subscription-types', SubscriptionTypeViewSet)
router.register(r'payment-methods', PaymentMethodViewSet)

urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("login/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("public-key/", public_key_view, name="public_key"),
    path('', include(router.urls)),
]
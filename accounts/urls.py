#accounts/urls.py

from django.urls import path, include
from .views import (
    CustomTokenObtainPairView, 
    CustomTokenRefreshView,
    LogoutView,
    public_key_view,
    ClinicOwnerProfileListCreateView,
    ClinicOwnerProfileDetailView,
    ClinicOwnerProfileMeView,
    ChangePasswordView,
    SuspendClinicView,
    RefundSubscriptionView,
    SubscriptionHistoryListCreateView,
    DoctorProfileListCreateView,
    DoctorProfileDetailView,
    ReceptionProfileListCreateView,
    ReceptionProfileDetailView,
    SubscriptionTypeListCreateView,
    SubscriptionTypeDetailView,
    PaymentMethodListCreateView,
    PaymentMethodDetailView,
)

urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("login/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("public-key/", public_key_view, name="public_key"),

    # Clinic Owner Profiles
    path('clinic-owner-profiles/', ClinicOwnerProfileListCreateView.as_view(), name='clinicownerprofile-list-create'),
    path('clinic-owner-profiles/me/', ClinicOwnerProfileMeView.as_view(), name='clinicownerprofile-me'),
    path('clinic-owner-profiles/<int:pk>/', ClinicOwnerProfileDetailView.as_view(), name='clinicownerprofile-detail'),
    path('clinic-owner-profiles/<int:pk>/suspend/', SuspendClinicView.as_view(), name='clinicownerprofile-suspend'),
    path('clinic-owner-profiles/<int:pk>/change-password/', ChangePasswordView.as_view(), name='clinicownerprofile-change-password'),
    path('clinic-owner-profiles/<int:clinic_pk>/subscriptions/', SubscriptionHistoryListCreateView.as_view(), name='clinic-subscription-history'),
    path('clinic-owner-profiles/<int:clinic_pk>/subscriptions/<int:sub_pk>/refund/', RefundSubscriptionView.as_view(), name='clinic-subscription-refund'),

    # Other Profiles and models
    path('doctor-profiles/', DoctorProfileListCreateView.as_view(), name='doctorprofile-list-create'),
    path('doctor-profiles/<int:pk>/', DoctorProfileDetailView.as_view(), name='doctorprofile-detail'),
    path('reception-profiles/', ReceptionProfileListCreateView.as_view(), name='receptionprofile-list-create'),
    path('reception-profiles/<int:pk>/', ReceptionProfileDetailView.as_view(), name='receptionprofile-detail'),
    path('subscription-types/', SubscriptionTypeListCreateView.as_view(), name='subscriptiontype-list-create'),
    path('subscription-types/<int:pk>/', SubscriptionTypeDetailView.as_view(), name='subscriptiontype-detail'),
    path('payment-methods/', PaymentMethodListCreateView.as_view(), name='paymentmethod-list-create'),
    path('payment-methods/<int:pk>/', PaymentMethodDetailView.as_view(), name='paymentmethod-detail'),
]
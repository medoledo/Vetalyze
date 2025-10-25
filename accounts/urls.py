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
    ManageSubscriptionStatusView,
    RefundSubscriptionView,
    SubscriptionHistoryListCreateView,
    DoctorProfileListCreateView,
    DoctorProfileDetailView,
    DoctorProfileMeView,
    ReceptionProfileListCreateView,
    ReceptionProfileDetailView,
    ReceptionProfileMeView,
    SubscriptionTypeListCreateView,
    SubscriptionTypeDetailView,
    PaymentMethodListCreateView,
    PaymentMethodDetailView,
)

urlpatterns = [
    # --- Authentication ---
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("public-key/", public_key_view, name="auth-public-key"),
    
    # Clinic Owner Profiles
    path('clinics/', ClinicOwnerProfileListCreateView.as_view(), name='clinic-list-create'),
    path('clinics/me/', ClinicOwnerProfileMeView.as_view(), name='clinic-me'),
    path('clinics/<int:pk>/', ClinicOwnerProfileDetailView.as_view(), name='clinic-detail'),
    path('clinics/<int:pk>/change-password/', ChangePasswordView.as_view(), name='clinic-change-password'),
    
    # Clinic Subscription Management
    path('clinics/<int:clinic_pk>/subscriptions/', SubscriptionHistoryListCreateView.as_view(), name='subscription-history-list-create'),
    path('clinics/<int:clinic_pk>/subscriptions/<int:sub_pk>/manage/', ManageSubscriptionStatusView.as_view(), name='subscription-manage'),
    path('clinics/<int:clinic_pk>/subscriptions/<int:sub_pk>/refund/', RefundSubscriptionView.as_view(), name='subscription-refund'),
    
    # Doctor Profiles
    path('doctors/', DoctorProfileListCreateView.as_view(), name='doctor-list-create'),
    path('doctors/me/', DoctorProfileMeView.as_view(), name='doctor-me'),
    path('doctors/<int:pk>/', DoctorProfileDetailView.as_view(), name='doctor-detail'),
    
    # Reception Profiles
    path('receptionists/', ReceptionProfileListCreateView.as_view(), name='receptionist-list-create'),
    path('receptionists/me/', ReceptionProfileMeView.as_view(), name='receptionist-me'),
    path('receptionists/<int:pk>/', ReceptionProfileDetailView.as_view(), name='receptionist-detail'),
    
    # Reference Data (Site Owner only)
    path('subscription-types/', SubscriptionTypeListCreateView.as_view(), name='subscription-type-list-create'),
    path('subscription-types/<int:pk>/', SubscriptionTypeDetailView.as_view(), name='subscription-type-detail'),
    path('payment-methods/', PaymentMethodListCreateView.as_view(), name='payment-method-list-create'),
    path('payment-methods/<int:pk>/', PaymentMethodDetailView.as_view(), name='payment-method-detail'),
]
# accounts/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date, timedelta
from decimal import Decimal
from .models import (
    User, Country, ClinicOwnerProfile, DoctorProfile, 
    ReceptionProfile, SubscriptionType, PaymentMethod, SubscriptionHistory
)
from .exceptions import (
    InactiveUserError, InactiveClinicError, 
    OverlappingSubscriptionError, SuspendedClinicError
)

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for the User model."""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'password': 'testpass123',
            'role': User.Role.CLINIC_OWNER
        }
    
    def test_create_user(self):
        """Test creating a new user."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.role, User.Role.CLINIC_OWNER)
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
    
    def test_user_roles(self):
        """Test different user roles."""
        for role in [User.Role.SITE_OWNER, User.Role.CLINIC_OWNER, 
                     User.Role.DOCTOR, User.Role.RECEPTION]:
            user = User.objects.create_user(
                username=f'user_{role}',
                password='testpass123',
                role=role
            )
            self.assertEqual(user.role, role)


class ClinicOwnerProfileModelTest(TestCase):
    """Test cases for ClinicOwnerProfile model."""
    
    def setUp(self):
        self.country = Country.objects.create(name='Egypt', max_phone_number=11)
        self.site_owner = User.objects.create_user(
            username='siteowner',
            password='testpass123',
            role=User.Role.SITE_OWNER
        )
        self.clinic_owner_user = User.objects.create_user(
            username='clinicowner',
            password='testpass123',
            role=User.Role.CLINIC_OWNER
        )
        self.clinic_profile = ClinicOwnerProfile.objects.create(
            user=self.clinic_owner_user,
            country=self.country,
            clinic_owner_name='Dr. Test',
            clinic_name='Test Clinic',
            owner_phone_number='01234567890',
            clinic_phone_number='01234567890',
            added_by=self.site_owner
        )
    
    def test_create_clinic_profile(self):
        """Test creating a clinic owner profile."""
        self.assertEqual(self.clinic_profile.clinic_name, 'Test Clinic')
        self.assertEqual(self.clinic_profile.status, ClinicOwnerProfile.Status.INACTIVE)
    
    def test_clinic_is_active_property(self):
        """Test is_active property."""
        self.assertFalse(self.clinic_profile.is_active)
        self.clinic_profile.status = ClinicOwnerProfile.Status.ACTIVE
        self.clinic_profile.save()
        self.assertTrue(self.clinic_profile.is_active)


class SubscriptionHistoryModelTest(TestCase):
    """Test cases for SubscriptionHistory model."""
    
    def setUp(self):
        self.country = Country.objects.create(name='Egypt', max_phone_number=11)
        self.site_owner = User.objects.create_user(
            username='siteowner',
            password='testpass123',
            role=User.Role.SITE_OWNER
        )
        self.clinic_owner_user = User.objects.create_user(
            username='clinicowner',
            password='testpass123',
            role=User.Role.CLINIC_OWNER
        )
        self.clinic_profile = ClinicOwnerProfile.objects.create(
            user=self.clinic_owner_user,
            country=self.country,
            clinic_owner_name='Dr. Test',
            clinic_name='Test Clinic',
            owner_phone_number='01234567890',
            clinic_phone_number='01234567890',
            added_by=self.site_owner
        )
        self.subscription_type = SubscriptionType.objects.create(
            name='Monthly',
            price=Decimal('100.00'),
            duration_days=30,
            allowed_accounts=5
        )
        self.payment_method = PaymentMethod.objects.create(name='Cash')
    
    def test_create_subscription(self):
        """Test creating a subscription."""
        subscription = SubscriptionHistory.objects.create(
            clinic=self.clinic_profile,
            subscription_type=self.subscription_type,
            payment_method=self.payment_method,
            amount_paid=Decimal('100.00'),
            start_date=date.today(),
            activated_by=self.site_owner
        )
        self.assertIsNotNone(subscription.end_date)
        self.assertEqual(subscription.status, SubscriptionHistory.Status.ACTIVE)
    
    def test_upcoming_subscription(self):
        """Test creating an upcoming subscription."""
        future_date = date.today() + timedelta(days=5)
        subscription = SubscriptionHistory.objects.create(
            clinic=self.clinic_profile,
            subscription_type=self.subscription_type,
            payment_method=self.payment_method,
            amount_paid=Decimal('100.00'),
            start_date=future_date,
            activated_by=self.site_owner
        )
        self.assertEqual(subscription.status, SubscriptionHistory.Status.UPCOMING)
    
    def test_days_left_property(self):
        """Test days_left property."""
        subscription = SubscriptionHistory.objects.create(
            clinic=self.clinic_profile,
            subscription_type=self.subscription_type,
            payment_method=self.payment_method,
            amount_paid=Decimal('100.00'),
            start_date=date.today(),
            activated_by=self.site_owner
        )
        expected_days = (subscription.end_date - date.today()).days
        self.assertEqual(subscription.days_left, max(0, expected_days))


class AuthenticationAPITest(APITestCase):
    """Test cases for authentication endpoints."""
    
    def setUp(self):
        self.client = APIClient()
        self.country = Country.objects.create(name='Egypt', max_phone_number=11)
        self.site_owner = User.objects.create_user(
            username='siteowner',
            password='testpass123',
            role=User.Role.SITE_OWNER
        )
        self.clinic_owner_user = User.objects.create_user(
            username='clinicowner',
            password='testpass123',
            role=User.Role.CLINIC_OWNER
        )
        self.clinic_profile = ClinicOwnerProfile.objects.create(
            user=self.clinic_owner_user,
            country=self.country,
            clinic_owner_name='Dr. Test',
            clinic_name='Test Clinic',
            owner_phone_number='01234567890',
            clinic_phone_number='01234567890',
            added_by=self.site_owner,
            status=ClinicOwnerProfile.Status.ACTIVE
        )
    
    def test_login_success(self):
        """Test successful login."""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'clinicowner',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['role'], User.Role.CLINIC_OWNER)
    
    def test_login_inactive_user(self):
        """Test login with inactive user."""
        self.clinic_owner_user.is_active = False
        self.clinic_owner_user.save()
        
        url = reverse('token_obtain_pair')
        data = {
            'username': 'clinicowner',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_login_inactive_clinic(self):
        """Test login with inactive clinic."""
        self.clinic_profile.status = ClinicOwnerProfile.Status.INACTIVE
        self.clinic_profile.save()
        
        url = reverse('token_obtain_pair')
        data = {
            'username': 'clinicowner',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_login_wrong_credentials(self):
        """Test login with wrong credentials."""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'clinicowner',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SubscriptionManagementTest(APITestCase):
    """Test cases for subscription management."""
    
    def setUp(self):
        self.client = APIClient()
        self.country = Country.objects.create(name='Egypt', max_phone_number=11)
        self.site_owner = User.objects.create_user(
            username='siteowner',
            password='testpass123',
            role=User.Role.SITE_OWNER
        )
        self.clinic_owner_user = User.objects.create_user(
            username='clinicowner',
            password='testpass123',
            role=User.Role.CLINIC_OWNER
        )
        self.clinic_profile = ClinicOwnerProfile.objects.create(
            user=self.clinic_owner_user,
            country=self.country,
            clinic_owner_name='Dr. Test',
            clinic_name='Test Clinic',
            owner_phone_number='01234567890',
            clinic_phone_number='01234567890',
            added_by=self.site_owner
        )
        self.subscription_type = SubscriptionType.objects.create(
            name='Monthly',
            price=Decimal('100.00'),
            duration_days=30,
            allowed_accounts=5
        )
        self.payment_method = PaymentMethod.objects.create(name='Cash')
        
        # Authenticate as site owner
        self.client.force_authenticate(user=self.site_owner)
    
    def test_create_subscription(self):
        """Test creating a new subscription."""
        url = reverse('subscription-history-list-create', kwargs={'clinic_pk': self.clinic_profile.user_id})
        data = {
            'subscription_type_id': self.subscription_type.id,
            'payment_method_id': self.payment_method.id,
            'amount_paid': '100.00',
            'start_date': str(date.today()),
            'extra_accounts_number': 0,
            'ref_number': 'REF123',
            'comments': 'Test subscription'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify clinic status is updated
        self.clinic_profile.refresh_from_db()
        self.assertEqual(self.clinic_profile.status, ClinicOwnerProfile.Status.ACTIVE)
    
    def test_overlapping_subscription(self):
        """Test preventing overlapping subscriptions."""
        # Create first subscription
        SubscriptionHistory.objects.create(
            clinic=self.clinic_profile,
            subscription_type=self.subscription_type,
            payment_method=self.payment_method,
            amount_paid=Decimal('100.00'),
            start_date=date.today(),
            activated_by=self.site_owner
        )
        
        # Try to create overlapping subscription
        url = reverse('subscription-history-list-create', kwargs={'clinic_pk': self.clinic_profile.user_id})
        data = {
            'subscription_type_id': self.subscription_type.id,
            'payment_method_id': self.payment_method.id,
            'amount_paid': '100.00',
            'start_date': str(date.today() + timedelta(days=10)),
            'extra_accounts_number': 0
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ManagementCommandTest(TestCase):
    """Test cases for the update_subscription_statuses management command."""
    
    def setUp(self):
        self.country = Country.objects.create(name='Egypt', max_phone_number=11)
        self.site_owner = User.objects.create_user(
            username='siteowner',
            password='testpass123',
            role=User.Role.SITE_OWNER
        )
        self.clinic_owner_user = User.objects.create_user(
            username='clinicowner',
            password='testpass123',
            role=User.Role.CLINIC_OWNER
        )
        self.clinic_profile = ClinicOwnerProfile.objects.create(
            user=self.clinic_owner_user,
            country=self.country,
            clinic_owner_name='Dr. Test',
            clinic_name='Test Clinic',
            owner_phone_number='01234567890',
            clinic_phone_number='01234567890',
            added_by=self.site_owner
        )
        self.subscription_type = SubscriptionType.objects.create(
            name='Monthly',
            price=Decimal('100.00'),
            duration_days=30,
            allowed_accounts=5
        )
        self.payment_method = PaymentMethod.objects.create(name='Cash')
    
    def test_activate_upcoming_subscription(self):
        """Test that upcoming subscriptions are activated on their start date."""
        # Create upcoming subscription with start date today
        subscription = SubscriptionHistory.objects.create(
            clinic=self.clinic_profile,
            subscription_type=self.subscription_type,
            payment_method=self.payment_method,
            amount_paid=Decimal('100.00'),
            start_date=date.today(),
            activated_by=self.site_owner,
            status=SubscriptionHistory.Status.UPCOMING
        )
        
        from django.core.management import call_command
        call_command('update_subscription_statuses')
        
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionHistory.Status.ACTIVE)
        
        self.clinic_profile.refresh_from_db()
        self.assertEqual(self.clinic_profile.status, ClinicOwnerProfile.Status.ACTIVE)
    
    def test_expire_subscription(self):
        """Test that active subscriptions are expired after their end date."""
        # Create subscription that ended yesterday
        subscription = SubscriptionHistory.objects.create(
            clinic=self.clinic_profile,
            subscription_type=self.subscription_type,
            payment_method=self.payment_method,
            amount_paid=Decimal('100.00'),
            start_date=date.today() - timedelta(days=31),
            activated_by=self.site_owner,
            status=SubscriptionHistory.Status.ACTIVE
        )
        subscription.end_date = date.today() - timedelta(days=1)
        subscription.save()
        
        self.clinic_profile.status = ClinicOwnerProfile.Status.ACTIVE
        self.clinic_profile.save()
        
        from django.core.management import call_command
        call_command('update_subscription_statuses')
        
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionHistory.Status.ENDED)
        
        self.clinic_profile.refresh_from_db()
        self.assertEqual(self.clinic_profile.status, ClinicOwnerProfile.Status.ENDED)

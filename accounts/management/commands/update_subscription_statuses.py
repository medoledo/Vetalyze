# accounts/management/commands/update_subscription_statuses.py

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from datetime import date
from accounts.models import SubscriptionHistory, ClinicOwnerProfile
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Updates subscription statuses based on current date. Should be run daily at 12:01 AM.'

    def handle(self, *args, **options):
        """
        Main command handler to update subscription statuses.
        This should be scheduled to run daily at 12:01 AM via cron or task scheduler.
        """
        today = date.today()
        
        self.stdout.write(self.style.NOTICE(f'Starting subscription status update for {today}'))
        
        upcoming_activated = 0
        subscriptions_expired = 0
        errors = 0
        
        try:
            # 1. Activate UPCOMING subscriptions that should start today
            upcoming_activated = self._activate_upcoming_subscriptions(today)
            
            # 2. End ACTIVE subscriptions that have expired
            subscriptions_expired = self._expire_active_subscriptions(today)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Subscription update completed successfully!\n'
                    f'- Activated: {upcoming_activated} subscriptions\n'
                    f'- Expired: {subscriptions_expired} subscriptions'
                )
            )
            
        except Exception as e:
            logger.exception(f"Error during subscription status update: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            errors = 1
        
        return errors

    @transaction.atomic
    def _activate_upcoming_subscriptions(self, today):
        """
        Activate UPCOMING subscriptions whose start_date is today or earlier.
        """
        upcoming_subs = SubscriptionHistory.objects.select_for_update().filter(
            status=SubscriptionHistory.Status.UPCOMING,
            start_date__lte=today
        ).select_related('clinic')
        
        activated_count = 0
        
        for sub in upcoming_subs:
            try:
                with transaction.atomic():
                    # End any currently active subscriptions for the same clinic
                    SubscriptionHistory.objects.filter(
                        clinic=sub.clinic,
                        status=SubscriptionHistory.Status.ACTIVE
                    ).update(status=SubscriptionHistory.Status.ENDED)
                    
                    # Activate the new subscription
                    sub.status = SubscriptionHistory.Status.ACTIVE
                    sub.save(update_fields=['status'])
                    
                    # Clinic status will automatically update (it's a computed property)
                    
                    activated_count += 1
                    logger.info(f"Activated subscription {sub.id} for clinic {sub.clinic.clinic_name}")
                    
            except Exception as e:
                logger.error(f"Failed to activate subscription {sub.id}: {str(e)}")
                continue
        
        return activated_count

    @transaction.atomic
    def _expire_active_subscriptions(self, today):
        """
        End ACTIVE subscriptions whose end_date has passed.
        """
        expired_subs = SubscriptionHistory.objects.select_for_update().filter(
            status=SubscriptionHistory.Status.ACTIVE,
            end_date__lt=today
        ).select_related('clinic')
        
        expired_count = 0
        
        for sub in expired_subs:
            try:
                with transaction.atomic():
                    # Mark subscription as ENDED
                    sub.status = SubscriptionHistory.Status.ENDED
                    sub.save(update_fields=['status'])
                    
                    # Clinic status will automatically update based on subscription history (it's a computed property)
                    
                    expired_count += 1
                    logger.info(f"Expired subscription {sub.id} for clinic {sub.clinic.clinic_name}")
                    
            except Exception as e:
                logger.error(f"Failed to expire subscription {sub.id}: {str(e)}")
                continue
        
        return expired_count

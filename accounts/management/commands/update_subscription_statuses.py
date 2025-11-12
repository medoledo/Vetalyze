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
        Creates new ENDED records for any currently ACTIVE subscriptions (preserves history).
        """
        upcoming_subs = SubscriptionHistory.objects.select_for_update().filter(
            status=SubscriptionHistory.Status.UPCOMING,
            start_date__lte=today
        ).select_related('clinic')
        
        activated_count = 0
        
        for sub in upcoming_subs:
            try:
                with transaction.atomic():
                    # Find any currently active subscriptions for the same clinic
                    active_subs = SubscriptionHistory.objects.filter(
                        clinic=sub.clinic,
                        status=SubscriptionHistory.Status.ACTIVE
                    ).select_related('subscription_type', 'payment_method', 'activated_by')
                    
                    # Create new ENDED records for each active subscription (preserves history)
                    for active_sub in active_subs:
                        # Check if this subscription group already has an ENDED record to avoid duplicates
                        already_ended = SubscriptionHistory.objects.filter(
                            subscription_group=active_sub.subscription_group,
                            status=SubscriptionHistory.Status.ENDED
                        ).exists()
                        
                        if already_ended:
                            logger.info(f"Subscription group {active_sub.subscription_group} already has ENDED record - skipping")
                            continue
                        
                        SubscriptionHistory.objects.create(
                            subscription_group=active_sub.subscription_group,
                            clinic=active_sub.clinic,
                            subscription_type=active_sub.subscription_type,
                            payment_method=active_sub.payment_method,
                            amount_paid=active_sub.amount_paid,
                            start_date=active_sub.start_date,
                            end_date=active_sub.end_date,
                            status=SubscriptionHistory.Status.ENDED,
                            comments=f"Ended by upcoming subscription activation on {today}",
                            activated_by=active_sub.activated_by
                        )
                    
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
        End ACTIVE subscriptions whose end_date has passed by creating a new ENDED record.
        This preserves the full subscription history (e.g., ACTIVE -> SUSPENDED -> ACTIVE -> ENDED).
        Only processes subscriptions that haven't been marked as ended yet.
        """
        expired_subs = SubscriptionHistory.objects.select_for_update().filter(
            status=SubscriptionHistory.Status.ACTIVE,
            end_date__lt=today
        ).select_related('clinic')
        
        expired_count = 0
        
        for sub in expired_subs:
            try:
                with transaction.atomic():
                    # Check if an ENDED record already exists for this subscription group
                    # This prevents duplicate ENDED records from multiple task runs or if already ended by activation
                    group_ended = SubscriptionHistory.objects.filter(
                        subscription_group=sub.subscription_group,
                        status=SubscriptionHistory.Status.ENDED
                    ).exists()
                    
                    if group_ended:
                        logger.info(f"Subscription group {sub.subscription_group} already has ENDED record - skipping subscription {sub.id}")
                        continue
                    
                    # Create a new record with ENDED status (preserves full history)
                    # The original ACTIVE record remains untouched
                    SubscriptionHistory.objects.create(
                        subscription_group=sub.subscription_group,
                        clinic=sub.clinic,
                        subscription_type=sub.subscription_type,
                        payment_method=sub.payment_method,
                        amount_paid=sub.amount_paid,
                        start_date=sub.start_date,
                        end_date=sub.end_date,
                        status=SubscriptionHistory.Status.ENDED,
                        comments=f"Subscription expired on {sub.end_date}",
                        activated_by=sub.activated_by,
                        extra_accounts_number=sub.extra_accounts_number,
                        ref_number=sub.ref_number
                    )
                    
                    # Clinic status will automatically update based on subscription history (it's a computed property)
                    
                    expired_count += 1
                    logger.info(f"Created ENDED record for subscription {sub.id} (clinic: {sub.clinic.clinic_name})")
                    
            except Exception as e:
                logger.error(f"Failed to expire subscription {sub.id}: {str(e)}")
                continue
        
        return expired_count


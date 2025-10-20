import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction, Product

audit_logger = logging.getLogger('audit')

@receiver(post_save, sender=Transaction)
def update_product_quantity(sender, instance, created, **kwargs):
    if created:
        product = instance.product
        if instance.transaction_type == 'sale':
            # Check for sufficient stock before deducting
            if product.quantity >= instance.quantity:
                product.quantity -= instance.quantity
                if product.is_returnable:
                    product.bottles_outstanding += instance.quantity
            else:
                # Handle the error case, maybe log it or raise an exception
                # This check is better placed in the view before saving
                audit_logger.error(f"Attempted to sell {instance.quantity} of {product.name} but only {product.quantity} available.")
                return # Stop processing
                
        elif instance.transaction_type == 'restock':
            product.quantity += instance.quantity

        product.save() # <-- This line MUST be uncommented
        
        # Log audit information
        audit_logger.info(
            f"Transaction {instance.id}: {instance.transaction_type} of {instance.quantity} "
            f"units on product {product.id} by user {instance.created_by}"
        )
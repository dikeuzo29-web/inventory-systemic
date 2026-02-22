import logging
from django.db.models.signals import post_save, pre_delete
from django.db import transaction
from .models import Transaction, Product, Sale, Saletem

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

@receiver(pre_delete, sender=Sale)
def restore_stock_when_sale_deleted(sender, instance, **kwargs):
    """
    When a Sale is deleted (including from Admin),
    restore stock for all its SaleItems.
    """

    with transaction.atomic():
        for item in instance.items.all():
            # Return quantity back to stock
            item.product.adjust_stock(item.quantity)


@receiver(pre_delete, sender=SaleItem)
def restore_stock_when_item_deleted(sender, instance, **kwargs):
    instance.product.adjust_stock(instance.quantity)

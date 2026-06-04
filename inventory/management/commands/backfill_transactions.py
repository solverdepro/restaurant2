"""
Management command to backfill InventoryTransaction records for existing
ProductBatches that were added before auto-transaction creation was enabled.

Usage:
    python manage.py backfill_transactions
"""

from django.core.management.base import BaseCommand
from inventory.models import ProductBatch, InventoryTransaction


class Command(BaseCommand):
    help = "Create Stock In transactions for batches that have none yet."

    def handle(self, *args, **options):
        created = 0
        skipped = 0

        for batch in ProductBatch.objects.all():
            # Only backfill if this batch has zero transactions
            if not InventoryTransaction.objects.filter(batch=batch).exists():
                InventoryTransaction.objects.create(
                    batch=batch,
                    transaction_type='Stock In',
                    quantity=batch.quantity,
                    unit_price=batch.price,
                    staff=None,
                    notes=f"Backfilled Stock In for batch {batch.batch_number}",
                )
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created transaction: {batch.product.name} — Batch {batch.batch_number}"
                    )
                )
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created {created} transaction(s), skipped {skipped} (already had transactions)."
            )
        )

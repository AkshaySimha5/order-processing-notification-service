from django.core.management.base import BaseCommand
from django.core.cache import cache
from pathlib import Path
import json
from decimal import Decimal

from orders.models import Product


PRODUCT_MASTER_PATH = Path(__file__).resolve().parent.parent.parent / "product_master.json"


class Command(BaseCommand):
    help = "Import products from product_master.json into Product model (upsert)."

    def handle(self, *args, **options):
        with open(PRODUCT_MASTER_PATH) as f:
            data = json.load(f)

        for p in data.get("products", []):
            obj, created = Product.objects.update_or_create(
                id=p["id"],
                defaults={
                    "name": p["name"],
                    "price": Decimal(p["price"]),
                },
            )
            action = "created" if created else "updated"
            self.stdout.write(f"{action}: Product {obj.id} - {obj.name}")

        # Clear cached product master so loader will repopulate
        cache.delete("product_master")
        self.stdout.write("product_master cache cleared")

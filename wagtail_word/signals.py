from django.dispatch import receiver
from django.db.models.signals import post_migrate
from wagtail.models import Collection

COLLECTION_NAME = "Wagtail Word"

@receiver(post_migrate)
def create_default_collection(sender, **kwargs):
    root: Collection = Collection.get_first_root_node()
    if not root:
        root = Collection.add_root(name="Root")

    if not Collection.objects.filter(name=COLLECTION_NAME).exists():
        root.add_child(name=COLLECTION_NAME)



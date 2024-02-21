from django.dispatch import receiver
from django.db.models.signals import post_migrate
from wagtail.models import Collection

COLLECTION_NAME = "Wagtail Word"

@receiver(post_migrate)
def create_default_collection(sender, **kwargs):
    root = Collection.get_first_root_node()
    if not root:
        Collection.add_root(name="Root")
    else:
        Collection.objects.get_or_create(name=COLLECTION_NAME, parent=root)



from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page
from wagtail.fields import (
    RichTextField,
)
from wagtail.admin.panels import (
    FieldPanel,
    ObjectList,
    TabbedInterface,
)
from .forms import WagtailWordPageForm

class BaseWordDocumentPage(models.Model):
    base_form_class = WagtailWordPageForm
    allow_styling = False

    content_panels = Page.content_panels + [
        FieldPanel('file'),
    ]

    class Meta:
        abstract = True

    def set_content(self, content: str):
        raise NotImplementedError

# Create your models here.
class WordDocumentPage(BaseWordDocumentPage):
    template = 'wagtail_word/page.html'

    content = RichTextField(
        blank=True,
        null=True,
        features=[
            "h1", "h2", "h3", "h4", "h5", "h6", 
            "bold", "italic", "ol", "ul", "link", 
            "document-link", "image", "embed", 
            "code", "blockquote", "superscript", 
            "subscript", "strikethrough", 
            "underline", "hr"
        ]
    )

    edit_panels = [
        FieldPanel('content'),
    ]

    edit_handler = TabbedInterface([
        ObjectList(BaseWordDocumentPage.content_panels, heading=_('Upload')),
        ObjectList(edit_panels, heading=_('Edit')),
        ObjectList(Page.promote_panels, heading=_('Promote')),
        ObjectList(Page.settings_panels, heading=_('Settings')),
    ])
    
    def set_content(self, content: str):
        self.content = content

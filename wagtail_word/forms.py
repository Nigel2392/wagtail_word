from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage

import docx
from docx import Document
from docx.document import Document as DocType
from docx.table import Table
from docx.text.run import Run
from docx.text.paragraph import Paragraph
from docx.text.hyperlink import Hyperlink
from docx.parts.image import ImagePart
from docx.text.font import Font

from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.images.models import AbstractImage
from wagtail.images import (
    get_image_model,
)

from collections import defaultdict
from typing import TYPE_CHECKING
import html
import zipfile

DOCX_EXTENSIONS = [
    '.docx',
    '.docm',
    '.doc',
]

if TYPE_CHECKING:
    from .models import BaseWordDocumentPage

import os

ALLOWED_EXTENSIONS = getattr(settings, "WAGTAILIMAGES_EXTENSIONS ", [
    "jpg", "jpeg", "png", "gif", "svg",
    "webp", "bmp", "tiff", "tif", "ico",
])

Image: AbstractImage = get_image_model()


def wrap_text_from_font(font: Font, text: str, allow_styling=False):

    text = html.escape(text)

    if font.all_caps:
        text = text.upper()

    if font.bold:
        text = f'<b>{text}</b>'
    if font.italic:
        text = f'<i>{text}</i>'
    if font.underline:
        text = f'<u>{text}</u>'
    if font.strike:
        text = f'<s>{text}</s>'

    if allow_styling:
        if font.color and font.color.rgb:
            text = f'<span style="color: {font.color.rgb}">{text}</span>'

    return text

def append_if_not_empty(d, chk_d, k, fn):
    v = chk_d[k]
    if v:
        d[k] = fn(v)

from lxml.etree import _Element
from docx.oxml.numbering import CT_Num

def is_ordered_list(document: DocType, paragraph: Paragraph) -> str:

    # Check if the paragraph is part of a list
    # If it is, return the appropriate tag
    
    numbering_part = document.part.numbering_part
    numId_elements = paragraph._element.xpath('./w:pPr/w:numPr/w:numId/@w:val')
    numId = None
    if numId_elements:
        numId = int(numId_elements[0])

    if numId is None:
        return "ul"

    # Access the numbering definition by numId
    numbering_def: _Element = numbering_part.numbering_definitions._numbering[numId]

    if (isinstance(numbering_def, CT_Num)):
        return "ul"

    if (isinstance(numbering_def, _Element)):
        return "ol"

    return "ul"



style_map = {
    'Heading 1': {
        "tag": 'h1',
    },
    'Heading 2': {
        "tag": 'h2',
    },
    'Heading 3': {
        "tag": 'h3',
    },
    'Heading 4': {
        "tag": 'h4',
    },
    'Heading 5': {
        "tag": 'h5',
    },
    'Heading 6': {
        "tag": 'h6',
    },
    'Title': {
        "tag": 'h1',
    },
    'Normal': {
        "tag": 'p',
    },
    'Quote': {
        "tag": 'blockquote',
    },
    'List Bullet': {
        "tag": 'li',
        'list_item_tag': is_ordered_list,
        "class": set(["list-bullet"]),
    },
    'List Number': {
        "tag": 'li',
        'list_item_tag': is_ordered_list,
        "class": set(["list-number"]),
    },
    'List Paragraph': {
        "tag": 'li',
        'list_item_tag': is_ordered_list,
        "class": set(["list-paragraph"]),
    },
}

def process_paragraph(document: DocType, paragraph: Paragraph, allow_styling=False):
    p = []
    if not paragraph.text.strip():
        return None, False
    
    # The paragraph can include hyperlinks, images, bold/italic/underlined text, etc
    # Process accordingly
    for item in paragraph.iter_inner_content():
        if isinstance(item, Hyperlink):
            # Process the hyperlink
            # This can include bold/italic/underlined text, etc
            l = []
            for r in item.runs:
                l.append(
                    wrap_text_from_font(r.font, r.text, allow_styling=allow_styling)
                )

            l = ''.join(l)
            p.append(
                f'<a href="{item.url}">{l}</a>'
            )
        elif isinstance(item, Run):
            # Process the run
            # This is regular text, it may include
            # bold/italic/underlined text, etc
            p.append(
                wrap_text_from_font(item.font, item.text, allow_styling=allow_styling)
            )

    # Join the text
    p = ''.join(p)
    attrs = defaultdict(set)

    # Check if we have special formatting
    if paragraph.alignment:
        attrs["class"].add(paragraph.alignment.name.lower())

    # Textcolor is not supported in wagtail richtext
    # Allow anyways.
    if allow_styling and paragraph.style.font.color and paragraph.style.font.color.rgb:
        attrs["style"].add(f'color: #{str(paragraph.style.font.color.rgb)}')

    # Appropriate tag/attributes for the style
    tag_data = style_map.get(paragraph.style.name, {
        "tag": 'p',
    })
    tag = tag_data['tag']

    kwgs = {}

    # Ugly - set the class and style attributes
    klass: set = tag_data.get('class', set())
    style: set = tag_data.get('style', set())

    # We might have a list item
    list_tag_fn = tag_data.get('list_item_tag', None)
    if list_tag_fn:
        list_tag = list_tag_fn(document, paragraph)
    else:
        list_tag = None

    klass.update(attrs.get("class", set()))
    style.update(attrs.get("style", set()))

    if klass:
        kwgs['class'] = ' '.join(klass)

    if style:
        kwgs['style'] = ';'.join(style)

    # Create the attribute string for HTML-text
    attr_string = ' '.join(
        f'{k}="{v}"' for k, v in kwgs.items()
    )

    return f'<{tag} {attr_string}>{p}</{tag}>', list_tag

def  process_image(document, paragraph: Paragraph, rels):
    for rId in rels:
        # Check if the image is in the paragraph
        if rId in paragraph._p.xml:
            # Save a wagtail image instance
            # This is so the richtext can handle it
            img = Image(
                file=rels[rId],
            )
            img.save()

            # Use a richtext-friendly tag
            return f'<embed embedtype="image" format="fullwidth" id="{img.id}" alt="{rels[rId]}" />'
    return None

def process_table(document, table: Table, rels, allow_styling=False):
    # print('Table', paragraph)
    table_list = []
    for row in table.rows:
        r = []
        for cell in row.cells:
            c = []
            for item in cell.iter_inner_content():
                # Recursively process the item as if 
                p = process_block(document, item, rels, allow_styling=allow_styling)
                if p is not None:
                    c.append(p)
            r.append(f'<td>{"".join(c)}</td>')
        table_list.append(f'<tr>{"".join(r)}</tr>')
    return f'<table>{"".join(table_list)}</table>'


def process_block(document: DocType, block, rels, allow_styling=False):
    # Process the content from the word document
    # So far supports:
    # - Paragraphs
    # - Tables
    # - Images
    # - Hyperlinks
    # - Single level lists (un-)ordered
    #       Any list will be assumed as single level.
    
    r = None
    list_tag = None
    if isinstance(block, Table):
        # Parse the table - table can include paragraphs, images, etc
        r = process_table(document, block, rels, allow_styling=allow_styling)

    elif isinstance(block, Paragraph) and 'Graphic' in block._p.xml:
        # Process the image
        r = process_image(document, block, rels)

    elif isinstance(block, Paragraph):
        # Process the paragraph
        # This can include hyperlinks, images, bold/italic/underlined text, etc
        r, list_tag = process_paragraph(document, block, allow_styling=allow_styling)

    return r, list_tag

class WagtailWordPageForm(WagtailAdminPageForm):
    file = forms.FileField(
        label=_('Word Document'),
        help_text=_('Upload a word document'),
        required=False,
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file:
            return file
        
        # Check if the extension is a valid .docx file
        found = False
        for ext in DOCX_EXTENSIONS:
            if file.name.endswith(ext):
                found = True
                break

        if not found:
            raise ValidationError(_('Invalid file extension'))

        # Open it to check
        # (I have no clue what security implications this has...)
        try:
            docx.Document(file)
        except Exception as e:
            raise ValidationError(_('Invalid .docx file'))
        return file
    
    def save(self, commit=True):
        instance: "BaseWordDocumentPage" = super().save(commit=False)
        file = self.cleaned_data['file']
        if file:

            document: DocType = Document(file)
            contents = []

            # Extract images from the document
            rels = {}
            zf = zipfile.ZipFile(file)
            for r in document.part.rels.values():
                if isinstance(r._target, ImagePart):
                    p = r._target.partname
                    ext = p.split('.')[-1]
                    if ext.lower() not in ALLOWED_EXTENSIONS:
                        continue

                    # Must use relative path (no leading slash)
                    if p.startswith('/'):
                        p = p[1:]

                    # Save the image to the storage
                    with zf.open(p) as f:
                        path = default_storage.save(
                            os.path.join(
                                f"wagtail_word/images/",
                                os.path.basename(r._target.partname)
                            ),
                            f,
                        )
                        rels[r.rId] = path

            # Make sure to parse as list so RichTextField can handle it
            list_tag = None
            was_tag = None
            for paragraph in document.iter_inner_content():
                was_tag = list_tag
                c, list_tag = process_block(
                    document,
                    paragraph,
                    rels,
                    instance.allow_styling,
                )

                # Probably better ways to do this...
                if list_tag and not was_tag:
                    contents.append(f'<{list_tag}>')
                elif was_tag and not list_tag:
                    contents.append(f'</{was_tag}>')
                elif was_tag and list_tag and was_tag != list_tag:
                    contents.append(f'</{was_tag}><{list_tag}>')
                    
                if c is not None:
                    contents.append(c)

            content = '\n'.join(contents)
            instance.set_content(content)

        if commit:
            instance.save()

        return instance
    
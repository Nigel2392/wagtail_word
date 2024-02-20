wagtail_word
============

A Wagtail module to display Word documents in the frontend.
Converts your word documents to richtext for easy editing in the Wagtail admin.

**Currently supported filetypes:**
- .docx
- .doc

**Currently supported content:**
- Text (Bold, underlines, italic, strikethrough)
   - Text suports colors with allow_styling=True
   - Colors get reset after saving the page in Wagtail admin for a second time.
- Images
- Tables
- Hyperlinks
- Lists
   - All will be converted to bullet points
   - Single level lists only

Quick start
-----------

1. Add 'wagtail_word' to your INSTALLED_APPS setting like this:

   ```
   INSTALLED_APPS = [
   ...,
   'wagtail_word',
   ]
   ```
2. Simply go to your Wagtail Admin.
3. Create a new Word Page.
4. Upload a file in the File field.
5. Save or publish the page and see the magic!

Base Class
-----------
We provide a base class to extend from. This class will provide you a predefined FieldPanel for the File, has the allow_styling attribute and a custom method to set the content to the right field for you to override.

```python
# Example class
class WordDocumentPage(BaseWordDocumentPage):
    template = 'wagtail_word/page.html'

    content = RichTextField(
        blank=True,
        null=True,
        features=[
            # Minimal required features for richtext
            "h1", "h2", "h3", "h4", "h5", "h6", 
            "bold", "italic", "ol", "ul", "link" "image", "embed", 
            "blockquote",
        ]
    )

    edit_panels = [
        FieldPanel('content'),
    ]

    edit_handler = TabbedInterface([
        ObjectList(BaseWordDocumentPage.content_panels, heading=_('Upload')),
        ObjectList(edit_panels, heading=_('Edit')),
        ...
    ])
    
    # Override this method to set the content to the right field
    def set_content(self, content: str):
        self.content = content

```
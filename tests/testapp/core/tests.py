from django.test import TestCase
from wagtail_word.forms import process_file
from django.conf import settings
from os import path


FILE_LOCATION = path.join(settings.BASE_DIR, "core/fixtures/test.docx")

# Create your tests here.
class WagtailWordTestCase(TestCase):
    def test_wagtail_word(self):
        content = process_file(FILE_LOCATION)
        print(content)
        self.assertEqual(content, """<h1 >Test</h1>
<h2 >Test</h2>
<h3 >Test</h3>
<h4 >Test</h4>
<h5 >Test</h5>
<h6 >Test</h6>
<p >This is a paragraph</p>
<p ><b>This is a bold paragraph</b></p>
<p ><i>This is an italic paragraph</i></p>
<p ><u>This is an underlined paragraph</u></p>
<p ><s>This paragraph has a strike through</s></p>
<ul>
<li class="list-paragraph">This is a list item</li>
</ul>""")
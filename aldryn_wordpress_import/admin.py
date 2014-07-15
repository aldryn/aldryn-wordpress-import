from django.contrib import admin, messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect

from .models import WordPressImport
from .utils import WordpressParser


class WordPressImportAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'created', 'xml_file', 'imported')
    raw_id_fields = ['author']
    fields = ['xml_file', 'target_language', ('create_authors', 'author'), 'log']

    def content_iterator(self, request, *args, **kwargs):
        yield ''
        yield super(WordPressImportAdmin, self).add_view(
            request, *args, **kwargs).content

    def add_view(self, request, *args, **kwargs):
        if request.method == 'POST':
            content_iterator = self.content_iterator(request, *args, **kwargs)
            response = HttpResponse(content_iterator, status=302)
            response['Location'] = reverse(
                'admin:aldryn_wordpress_import_wordpressimport_changelist')
            messages.success(request, 'Wordpress Import added succesfully')
            return response
        return super(WordPressImportAdmin, self).add_view(
            request, *args, **kwargs)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST' and 'execute' in request.POST:
            instance = self.get_object(request, object_id)
            parser = WordpressParser(wp_import=instance)
            log = parser.parse(instance)
            instance.log = log
            instance.imported = True
            instance.save()
            url = reverse(
                'admin:aldryn_wordpress_import_wordpressimport_change',
                args=(object_id,))
            return redirect(url)
        return super(WordPressImportAdmin, self).change_view(
            request, object_id, form_url, extra_context)

admin.site.register(WordPressImport, WordPressImportAdmin)

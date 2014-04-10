from django.contrib import admin
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from .models import WordPressImport
from .utils import WordpressParser


class WordPressImportAdmin(admin.ModelAdmin):
    list_display = ('author', 'created', 'xml_file', 'imported')
    raw_id_fields = ['author']

    def content_iterator(self, request, *args, **kwargs):
        yield ''
        yield super(WordPressImportAdmin, self).add_view(
            request, *args, **kwargs).content

    def add_view(self, request, *args, **kwargs):
        data = request.GET.copy()
        data['author'] = request.user.id  # default author is logged-in user
        request.GET = data
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
            parser = WordpressParser(request)
            instance = self.get_object(request, object_id)
            log = parser.parse(instance.xml_file)
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

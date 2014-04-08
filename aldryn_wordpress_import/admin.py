from django.contrib import admin
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from .models import WordPressImport
from .utils import WordpressParser


class WordPressImportAdmin(admin.ModelAdmin):
    change_form_template = 'admin/aldryn_wordpress_import/change_form.html'
    list_display = ('author', 'created', 'imported')
    raw_id_fields = ['author']

    def add_view(self, request, *args, **kwargs):
        data = request.GET.copy()
        data['author'] = request.user.id  # default author is logged-in user
        request.GET = data
        return super(WordPressImportAdmin, self).add_view(request, *args, **kwargs)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST' and 'execute' in request.POST:
            parser = WordpressParser(user=request.user)
            instance = self.get_object(request, object_id)
            log = parser.parse(instance.xml_file.path)
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

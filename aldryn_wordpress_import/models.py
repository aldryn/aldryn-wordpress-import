from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class WordPressImport(models.Model):
    author = models.ForeignKey(
        User, verbose_name=_('Default author'), null=True, blank=True,
        help_text=_('Ignored if "Create authors" is selected'))
    create_authors = models.BooleanField(_('Create authors'), default=True)
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    imported = models.BooleanField(_('Imported'), default=False, editable=False)
    log = models.TextField(_('Log'), null=True, blank=True)
    target_language = models.CharField(_('Target language'), max_length=10, choices=settings.LANGUAGES)
    xml_file = models.FileField(_('Wordpress Export file'), upload_to='imports/%Y/%m/%d')

    def __str__(self):
        return 'WordPressImport @ %s - %s' % (self.created, self.imported)

    class Meta:
        verbose_name = 'WordPress Import'
        verbose_name_plural = 'WordPress Imports'

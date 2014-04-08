from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class WordPressImport(models.Model):
    author = models.ForeignKey(User,verbose_name=_('Author'))
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    imported = models.BooleanField(_('Imported'), default=False,
                                   editable=False)
    log = models.TextField(_('Log'), null=True, blank=True)
    xml_file = models.FileField(_('Wordpress Export file'),
                                upload_to='imports/%Y/%m/%d')

    def __str__(self):
        return 'WordPressImport @ %s - %s' % (self.created,
                                              self.imported)

    class Meta:
        verbose_name = 'WordPress Import'
        verbose_name_plural = 'WordPress Imports'

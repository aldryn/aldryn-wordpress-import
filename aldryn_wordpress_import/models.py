from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class WordPressImport(models.Model):
    STATUS_CHOICES = (
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('inprogress', _('In progress')),
        ('new', _('New'))
    )
    author = models.ForeignKey(User, editable=False, verbose_name=_('Author'))
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    status = models.CharField(_('Status'), editable=False, max_length=10,
                              choices=STATUS_CHOICES)
    log = models.TextField(_('Log'), null=True, editable=False)
    xml_file = models.FileField(_('Wordpress Export file'))

    def __str__(self):
        return 'WordPressImport @ %s - %s' % (self.created,
                                              self.get_status_display())

from django.core.management.base import BaseCommand

from ...models import WordPressImport
from ...utils import WordpressParser


class Command(BaseCommand):
    args = '<wordpressimport_id>'
    help = 'Executed the specified import'

    def handle(self, *args, **options):
        wp_import = WordPressImport.objects.get(pk=int(args[0]))
        parser = WordpressParser(wp_import=wp_import)
        log = parser.parse(wp_import.xml_file)
        wp_import.log = log
        wp_import.imported = True
        wp_import.save()

        self.stdout.write('Successfully imported "%s"' % wp_import)

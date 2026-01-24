# ==============================================================================
# NEWSFILTERAI - SEED DOMAIN LISTS COMMAND
# ==============================================================================
# Команда для ініціалізації білого та чорного списків доменів у Redis

from django.core.management.base import BaseCommand
from news.services import domain_list_service
from news.models import DomainReputation


class Command(BaseCommand):
    """
    Заповнює Redis та PostgreSQL початковими даними для списків доменів.

    Використання:
        python manage.py seed_domain_lists
        python manage.py seed_domain_lists --clear  # Очистити перед заповненням
    """

    help = 'Ініціалізує білий та чорний списки доменів у Redis та PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистити існуючі списки перед заповненням'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('🚀 Ініціалізація списків доменів...'))

        if options['clear']:
            self._clear_lists()

        # Заповнюємо Redis
        redis_result = domain_list_service.seed_default_lists()

        self.stdout.write(
            f"  ✅ Redis: додано {redis_result['whitelist_added']} до whitelist, "
            f"{redis_result['blacklist_added']} до blacklist"
        )

        # Синхронізуємо з PostgreSQL
        db_result = self._sync_to_database()

        self.stdout.write(
            f"  ✅ PostgreSQL: додано {db_result['created']} записів"
        )

        # Виводимо статистику
        stats = domain_list_service.get_stats()
        self.stdout.write(self.style.SUCCESS(
            f"\n📊 Підсумок:\n"
            f"   Білий список: {stats['whitelist_count']} доменів\n"
            f"   Чорний список: {stats['blacklist_count']} доменів"
        ))

    def _clear_lists(self):
        """Очищає існуючі списки"""
        self.stdout.write(self.style.WARNING('  🗑️  Очищення існуючих списків...'))

        # Очищаємо Redis
        from django_redis import get_redis_connection
        from django.conf import settings

        redis = get_redis_connection("default")
        redis.delete(settings.REDIS_WHITELIST_KEY)
        redis.delete(settings.REDIS_BLACKLIST_KEY)

        # Очищаємо PostgreSQL
        DomainReputation.objects.all().delete()

        self.stdout.write('  ✅ Списки очищено')

    def _sync_to_database(self) -> dict:
        """Синхронізує Redis списки з PostgreSQL"""
        created_count = 0

        # Отримуємо домени з Redis
        whitelist = domain_list_service.get_whitelist()
        blacklist = domain_list_service.get_blacklist()

        # Додаємо до PostgreSQL (якщо ще не існують)
        for domain in whitelist:
            _, created = DomainReputation.objects.get_or_create(
                domain=domain,
                defaults={
                    'reputation_type': DomainReputation.ReputationType.WHITELIST,
                    'added_by': 'system (seed)',
                    'description': 'Додано автоматично при ініціалізації'
                }
            )
            if created:
                created_count += 1

        for domain in blacklist:
            _, created = DomainReputation.objects.get_or_create(
                domain=domain,
                defaults={
                    'reputation_type': DomainReputation.ReputationType.BLACKLIST,
                    'added_by': 'system (seed)',
                    'description': 'Додано автоматично при ініціалізації'
                }
            )
            if created:
                created_count += 1

        return {'created': created_count}


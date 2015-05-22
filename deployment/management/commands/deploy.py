from django.core.management.base import BaseCommand

from fabric.api import env, execute

from deployment.fabfile import deploy

class Command(BaseCommand):
    help = "Deploys the project to the server"

    def handle(self, *args, **options):
        env.hosts = ["uem.monagis.com"]
        env.username = "root"
        env.password = "mnwp4$$"
        execute(deploy)


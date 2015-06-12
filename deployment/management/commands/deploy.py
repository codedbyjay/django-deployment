from optparse import make_option

from django.core.management.base import BaseCommand

from fabric.api import env, execute

from deployment.fabfile import deploy
from deployment import setup_fabric_environment

class Command(BaseCommand):
    help = "Deploys the project to the server"

    option_list = BaseCommand.option_list + (
        make_option('--server',
            dest='server',
            default=None,
            help='The server to deploy to'),
        )

    def handle(self, *args, **options):
        if not options["server"]:
            print("Please specify a server name with --server")
        setup_fabric_environment(options["server"])
        execute(deploy)


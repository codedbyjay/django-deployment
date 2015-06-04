import os
from os.path import expanduser
import getpass
import socket
from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings

from fabric.api import execute, env, run, sudo, cd
from fabric.contrib.files import append
import pyrax 
import ConfigParser

from deployment.fabfile import get_config
from deployment import setup_fabric_environment, add_server_config


class Command(BaseCommand):
    help = "Creates a DEPLOY_rackspace server"

    option_list = BaseCommand.option_list + (
        make_option('--account',
            dest='account',
            default=None,
            help='The Rackspace account name'),
        make_option('--api-key',
            dest='api_key',
            default=None,
            help='The Rackspace API key '),
        make_option('--server',
            dest='server',
            default=None,
            help='The server to deploy to'),
        make_option('--image',
            dest='image',
            default=None,
            help='The image to deploy to'),
        make_option('--flavor',
            dest='flavor',
            default=None,
            help='The flavor to deploy to'),
        )

    def save_credentials(self, server_name, user, password, ip):
        add_server_config(server_name, user, password, ip)

    def handle(self, *args, **options):
        pyrax.set_setting("identity_type", "rackspace")
        pyrax.set_default_region('DFW')
        account = options["account"] or get_config('rackspace', 'username')
        api_key = options["api_key"] or get_config('rackspace', 'api_key')

        if not account:
            print("Please provide your username by using --account or in DEPLOY_CONFIG['rackspace']['username']")
            return

        if not api_key:
            print("Please provide your username by using --api-key or in DEPLOY_CONFIG['rackspace']['api_key']")
            return

        pyrax.set_credentials(account, api_key)

        server_name = options["server"]
        if not server_name:
            print("Please provide a server name with --server")
            return

        print("Contacting Rackspace")
        cs = pyrax.cloudservers
        servers = cs.list()

        for server in servers:
            if server.name == server_name:
                print("Nothing to do, %s already exists" % server_name)
                return 

        # Create the server
        default_image = options["image"] or get_config('rackspace', 'default_image')
        default_flavor = options["flavor"] or get_config('rackspace', 'default_flavor')

        if not default_image:
            print "Select an image"
            images = sorted(cs.list_images(), key=lambda image: image.name)
            for i in range(len(images)):
                image = images[i]
                print " %s. %s (%s)" % (i+1, image.name, image.id)

            selected_image_index = input("Which image should we build? ")
            selected_image = images[selected_image_index - 1]

            print("")
            print("Will build image: %s" % selected_image.name)
            print("")
        else:
            selected_image = cs.images.get(default_image)

        if not default_flavor:
            print "Select flavor"
            flavors = sorted(cs.list_flavors(), key=lambda flavor: flavor.name)

            for i in range(len(flavors)):
                flavor = flavors[i]
                print " %s. %s (%s)" % (i+1, flavor.name, flavor.id)

            selected_flavor_index = input("Which flavor should we build? ")
            selected_flavor = flavors[selected_flavor_index - 1]

            print("")
            print("Will build flavor: %s" % selected_flavor.name)
            print("")
        else:
            selected_flavor = cs.flavors.get(default_flavor)


        confirmation = unicode(raw_input("Go ahead and build %s %s? [Y/n] " % (selected_image.name, selected_flavor.name))) or ""
        if confirmation.lower() in ["n", "no"]:
            print("Exiting ...")
            return

        print("")
        print("............................")
        print("Building the server")
        server = cs.servers.create(server_name, selected_image.id, selected_flavor.id, 
            key=api_key)
        admin_psw = server.adminPass
        pyrax.utils.wait_for_build(server)

        print("Server is ready!")
        server = cs.servers.get(server.id)
        ips = [ ip for ip in server.networks.get("public") if ip.count(".") == 3 ]
        ip = ips[0]

        print("Writing credentials file")
        # write it to a file 
        self.save_credentials(server_name, "root", admin_psw, ip)

        print("All done")

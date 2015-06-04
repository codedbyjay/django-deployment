import os
import ConfigParser
from StringIO import StringIO

from django.conf import settings as django_settings

from fabric.api import execute, env, run, sudo, cd, put
from fabric.contrib.files import append
from fabric.context_managers import settings

def setup_fabric_environment(server_name):
    """ Reads the server.cfg file and grabs the credentials for the server `server_name`
        and places those credentials in the fabric `env` variable to allow us 
        to connect seemlessly to our servers.
    """
    if not server_name:
        raise Exception("Please supply a proper server name")
    config_file = "%s/server.cfg" % django_settings.BASE_DIR
    if not os.path.exists(config_file):
        raise Exception("No server.cfg found, please make one")
        return

    # Read in the config
    config = ConfigParser.RawConfigParser()
    config.read(config_file)

    user = config.get(server_name, "user")
    password = config.get(server_name, "password")
    ip = config.get(server_name, "ip")
    env["user"] = user
    env["password"] = password
    env["hosts"] = [ip] 


def add_server_config(server_name, user, password, ip):
    config = ConfigParser.RawConfigParser()
    config.add_section(server_name)
    config.set(server_name, "user", user)
    config.set(server_name, "password", password)
    config.set(server_name, "ip", ip)
    with open("%s/server.cfg" % django_settings.BASE_DIR, "a") as config_file:
        config.write(config_file)

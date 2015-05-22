from StringIO import StringIO
import os
import json

from django.template.loader import get_template
from django.template import Context

from fabric.contrib.files import exists
from fabric.api import (
    cd, settings, local, run, sudo, env, put
)

import deployment
from deployment.bb import deploy_key_exists, add_deploy_key

solo_rb = """
root = "%s"
file_cache_path root
cookbook_path root + '/cookbooks'
"""

DEPLOY_CONFIG_DEFAULT = {
    "python" :
    {
        "install_method" : "package"
    },
    "run_list": [ 
        # "recipe[deployment::default]",
        # "recipe[apt]", 
        # "recipe[python]", 
        "recipe[database::postgresql]",
        # "recipe[deployment::setup_postgres]",
     ],
    # configuration for PostgreSQL
    "postgresql" : {
        "version" : "9.3",
        "enable_pgdg_apt" : "true",
        "dir": "/etc/postgresql/9.3/main",
        "config" : {
            "listen_addresses" : "localhost",
            "log_rotation_age": "1d",
            "log_rotation_size": "10MB",
            "log_filename": "postgresql-%Y-%m-%d_%H%M%S.log",
            "data_directory": "/var/lib/postgresql/9.3/main",
            "hba_file": "/etc/postgresql/9.3/main/pg_hba.conf",
            "ident_file" : "/etc/postgresql/9.3/main/pg_ident.conf",
            "external_pid_file" : "/var/run/postgresql/9.3-main.pid"
        },
        "client": {
            "packages": ["postgresql-client-9.3"]
        },
        "server": {
            "packages": ["postgresql-9.3", "postgresql-server-dev-9.3"]
        },
        "contrib": {
            "packages": ["postgresql-contrib-9.3"]
        },
        "password": {
            "postgres": "password"
        },
        "pg_hba": [
          {"type": "local", "db": "all", "user": "all", "addr": "", "method": "trust"},
          {"type": "host", "db": "all", "user": "all", "addr": "127.0.0.1/32", "method": "trust"},
          {"type": "host", "db": "all", "user": "all", "addr": "::1/128", "method": "trust"}
      ]
    },
    "project" : {
        "database" : {
            "name" : "project",
            "user" : "user",
            "password" : "password",
        },
        "deployment" : {
            "username" : "ubuntu",
            "password" : "ubuntu",
            "database_name" : "project",
            "database_user" : "user",
            "database_password" : "password",
            "server_name" : "My Project",
            "site_url" : "http://localhost",
            "gunicorn_port" : 8000,
        }
    }
}
DEPLOY_CONFIG = {}

def deploy():
    """ Deploys the Django application
    """
    print("Deploying Django application")
    from django.conf import settings as django_settings
    # Gather some variables
    username = getattr(django_settings, "DEPLOY_USERNAME", "ubuntu")
    password = getattr(django_settings, "DEPLOY_PASSWORD", "ubuntu")
    home_dir = "/home/%s" % username
    ssh_dir = "%s/.ssh" % home_dir
    ssh_key_filename = "%s/id_rsa.pub" % ssh_dir
    ssh_private_key_filename = os.path.splitext(ssh_key_filename)[0]
    deploy_dir = getattr(django_settings, 
        "DEPLOY_DIRECTORY",
        "%s/web" % home_dir
    )
    git_branch = getattr(django_settings, "DEPLOY_BRANCH", "master")
    repository_url = getattr(settings, 
        "REPOSITORY_URL", local("git config --get remote.origin.url", 
        capture=True))
    project_name = os.path.splitext(repository_url.split("/")[-1])[0]
    project_dir = "%s/%s" % (deploy_dir, project_name)
    deploy_key_name = "%s-%s" % (project_name, env.host)

    with settings(warn_only=True):
        # make sure the user exists
        if not run("getent passwd %s" % username, quiet=True):
            print("Creating user: %s" % username)
            sudo("useradd %s" % username)
            sudo("echo %s:%s | chpasswd" % (username, password))

        with cd(home_dir):
            # make sure the deploy dir exists...
            sudo("mkdir -p %s" % deploy_dir, quiet=True, user=username)
            # make sure we have a SSH key
            if not exists(ssh_key_filename):
                sudo('ssh-keygen -q -t rsa -f %s -N ""' % ssh_private_key_filename, 
                    quiet=True, user=username)
                result = sudo("cat %s" % ssh_key_filename)
                sudo('echo -e "Host bitbucket.org\n\tStrictHostKeyChecking no\n" >> %s/config'% ssh_dir, quiet=True, user=username)

            if "bitbucket.org" in repository_url.lower():
                # Make sure a deployment key is added for the project
                ssh_key = sudo("cat %s" % ssh_key_filename, user=username)
                if not deploy_key_exists(ssh_key, project_name=project_name):
                    add_deploy_key(ssh_key, project_name=project_name, 
                        label=deploy_key_name)

            if run("chef --version").failed:
                print("Installing ChefDK")
                with cd("/tmp/"):
                    sudo("wget https://opscode-omnibus-packages.s3.amazonaws.com/ubuntu/12.04/x86_64/chefdk_0.5.1-1_amd64.deb")
                    sudo("dpkg -i chefdk_0.5.1-1_amd64.deb")
                    sudo("rm chefdk_0.5.1-1_amd64.deb")
            if run("git --version").failed:
                print("Installing Git")
                sudo("apt-get install -y git")

        # Now to check out the project
        with cd(deploy_dir):
            with settings(user=username, password=password):
                if not exists(project_name):
                    print("Cloning url: %s in directory: %s" % (repository_url, deploy_dir))
                    run("git clone %s" % repository_url)
                else:
                    print("Repository already cloned... moving on")

                with cd(project_name):
                    print("Pulling the latest code")
                    run("git pull")
                    run("git checkout %s" % git_branch)
                    run("git pull")
                    # Run chef
                    # Setup solo.rb
                    solo_rb_contents = StringIO(solo_rb % project_dir)
                    put(local_path=solo_rb_contents, remote_path="%s/solo.rb" % project_dir)
                    solo_json_contents = StringIO(get_solo_json())
                    put(local_path=solo_json_contents, remote_path="%s/solo.json" % project_dir)
                    # Push up the cookbooks
                    deployment_cookbooks = os.path.join(os.path.dirname(deployment.__file__), "..", "cookbooks")
                    put(local_path=deployment_cookbooks, remote_path=project_dir)
                    # Write the template files out to cookbooks/deployment/templates/default dir on the server
                    deployment_module_path = os.path.dirname(deployment.__file__)
                    deployment_template_dir = os.path.join(deployment_module_path, "templates", "deployment")
                    for template_name in os.listdir(deployment_template_dir):
                        template_context = Context({})
                        template_contents = StringIO(get_template("deployment/%s" % template_name).render(template_context))
                        put(local_path=template_contents, 
                            remote_path=os.path.join(
                                    project_dir, 'cookbooks', 'deployment', 
                                    'templates', 'default', template_name
                                )
                            )
                    with cd("cookbooks"):
                        # Download extra cookbooks if necessary
                        for cookbook in get_cookbooks():
                            filename = "%s*.tar.gz" % cookbook
                            if not exists(filename):
                                print("Downloading cookbook: %s" % cookbook)
                                run("knife cookbook site download %s" % cookbook)
                        zipped_cookbooks = run("ls *.tar.gz").split()
                        for zipped_cookbook in zipped_cookbooks:
                            print("Extracting %s" % zipped_cookbook)
                            run("tar xvf %s" % zipped_cookbook)


        # Run Chef as root
        with cd(project_dir):
            sudo("chef-solo -c solo.rb -j solo.json")

def get_cookbooks():
    """ Returns a list of cookbooks needed 
    """
    from django.conf import settings as django_settings
    cookbooks = [
        "apt",
        "build-essential",
        "apache2",
        "python",
        "database",
        "postgresql",
        "openssl",
        "chef-sugar",
    ]
    cookbooks.extend(getattr(django_settings, "DEPLOY_COOKBOOKS", []))
    return cookbooks


def get_config():
    """ Gets the configuration for solo.json file
    """
    from django.conf import settings as django_settings
    if not DEPLOY_CONFIG:
        DEPLOY_CONFIG.update(DEPLOY_CONFIG_DEFAULT)
        setting_overrides = {
            "site_url" : getattr(django_settings, "SITE_URL", "http://localhost"),
        }
        DEPLOY_CONFIG.update(setting_overrides)
    return DEPLOY_CONFIG_DEFAULT

def add_config(config, override=True):
    """ Adds configuration for solo.json 
    """
    current_config = get_config()
    if override:
        current_config.update(config)
    else:
        config = config.copy()
        config.update(current_config)
        current_config.update(config)

def get_solo_json():
    """ Return the JSON for the solo.json file
    """
    output = json.dumps(get_config())
    return output

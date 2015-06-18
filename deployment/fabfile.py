from StringIO import StringIO
import os
import json
from pprint import pprint

from django.template.loader import get_template
from django.template import Context

from fabric.contrib.files import exists
from fabric.api import (
    cd, settings, local, run, sudo, env, put
)

import deployment
from deployment.bb import deploy_key_exists, add_deploy_key

def dict_merge(a, b, path=None):
    """
        Obtained from http://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge
    """
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dict_merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                pass # keep a's value
        else:
            a[key] = b[key]
    return a

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
        "recipe[deployment::setup_postgres]",
        "recipe[deployment::default]",
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
        'extensions' : ['postgis'],
        "client": {
            "packages": ["postgresql-client-9.3"]
        },
        "server": {
            "packages": ["postgresql-9.3", "postgresql-server-dev-9.3"]
        },
        "contrib": {
            "packages": [
                "postgresql-contrib-9.3", 
                "postgresql-9.3-postgis-2.1", 
                "postgresql-9.3-postgis-scripts"
            ]
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
            "username" : "user",
            "password" : "password",
            "host" : "",
            "port" : "",
            "engine" : "django.contrib.gis.db.backends.postgis",
        },
        "django" : {
            "commands" : ["syncdb --noinput", "migrate --noinput"],
            "initial_data" : []
        },
        "deployment" : {
            "username" : "ubuntu",
            "password" : "ubuntu",
            "deploy_dir" : "/home/ubuntu/web",
            "project_dir" : "/home/ubuntu/web/project",
            "server_name" : "My Project",
            "site_url" : "http://localhost",
            "gunicorn_port" : 8000,
            "apt_packages" : [
                "graphviz", "libgraphviz-dev", "pkg-config",
                "python-virtualenv", "make", "build-essential",
                "python-dev", "libxml2-dev", "libxslt1-dev",
                "binutils", "libproj-dev", "gdal-bin", "postgis",
                "nginx"
            ]
        },
        "apt" : {
            "packages" : [],
            "ppas" : []
        }
    },
    'rackspace': {
        'default_image' : '598a4282-f14b-4e50-af4c-b3e52749d9f9',
        'default_flavor' : 'general1-1',
        'username' : None,
        'api_key' : None
    },
    'bitbucket' : {
        'username' : None,
        'client_key' : None,
        'client_secret' : None,
        'access_token' : None,
        'access_token_secret' : None
    }
}
DEPLOY_CONFIG = {}

def deploy():
    """ Deploys the Django application
    """
    print("Deploying Django application")
    # print(json.dumps(get_config(), indent=4, sort_keys=True))
    from django.conf import settings as django_settings
    # Gather some variables
    username = get_config("project", "deployment", "username")
    password = get_config("project", "deployment", "password")
    home_dir = get_config("project", "deployment", "home_dir")
    ssh_dir = get_config("project", "deployment", "ssh_dir")
    ssh_key_filename = "%s/id_rsa.pub" % ssh_dir
    ssh_private_key_filename = os.path.splitext(ssh_key_filename)[0]
    deploy_dir = get_config("project", "deployment", "deploy_dir")
    git_branch = get_config("project", "deployment", "git_branch")
    repository = get_config("project", "deployment", "git_repository")
    project_name = get_config("project", "deployment", "project_name")
    project_dir = get_config("project", "deployment", "project_dir")
    deploy_key_name = "%s-%s" % (project_name, env.host)
    ppas = get_config("project", "apt", "ppas")
    packages = get_config("project", "apt", "packages")
    for ppa in ppas:
        sudo("apt-add-repository -y %s" % ppa)
    sudo("apt-get update --fix-missing", quiet=True) # always start with this...
    if packages:
        sudo("apt-get install -y --no-install-recommends %s" % " ".join(packages))

    with settings(warn_only=True):
        # make sure the user exists
        if not run("getent passwd %s" % username, quiet=True):
            print("Creating user: %s with password: %s" % (username, password))
            sudo("useradd %s" % username)
            sudo("echo %s:%s | chpasswd" % (username, password))

        sudo("mkdir -p %s" % home_dir, quiet=True)
        with cd(home_dir):
            # make sure the deploy dir exists...
            sudo("mkdir -p %s" % deploy_dir, quiet=True)
            # make sure we have a SSH key
            if not exists(ssh_key_filename):
                sudo('ssh-keygen -q -t rsa -f %s -N ""' % ssh_private_key_filename, 
                    quiet=True)
                result = sudo("cat %s" % ssh_key_filename)
                sudo('echo -e "Host bitbucket.org\n\tStrictHostKeyChecking no\n" >> %s/config'% ssh_dir, quiet=True)

            if "bitbucket.org" in repository.lower():
                # Make sure a deployment key is added for the project
                ssh_key = sudo("cat %s" % ssh_key_filename)
                if not deploy_key_exists(ssh_key, project_name=project_name):
                    add_deploy_key(ssh_key, project_name=project_name, 
                        label=deploy_key_name)

            if run("chef --version", quiet=True).failed:
                print("Installing ChefDK")
                with cd("/tmp/"):
                    sudo("wget https://opscode-omnibus-packages.s3.amazonaws.com/ubuntu/12.04/x86_64/chefdk_0.5.1-1_amd64.deb", quiet=True)
                    sudo("dpkg -i chefdk_0.5.1-1_amd64.deb", quiet=True)
                    sudo("rm chefdk_0.5.1-1_amd64.deb", quiet=True)
            if run("git --version", quiet=True).failed:
                print("Installing Git")
                sudo("apt-get install -y git")

        # Now to check out the project
        with cd(deploy_dir):
            if not exists(project_name):
                print("Cloning url: %s in directory: %s" % (repository, deploy_dir))
                clone_command = "git clone %s" % repository
                run(clone_command, quiet=True)
            else:
                print("Repository already cloned... moving on")

            with cd(project_name):
                print("Pulling the latest code")
                run("git pull", quiet=True)
                run("git checkout %s" % git_branch, quiet=True)
                run("git pull", quiet=True)
                # Run chef
                # Setup solo.rb
                solo_rb_contents = StringIO(solo_rb % project_dir)
                put(local_path=solo_rb_contents, remote_path="%s/solo.rb" % project_dir)
                solo_json_contents = StringIO(get_solo_json())
                put(local_path=solo_json_contents, remote_path="%s/solo.json" % project_dir)
                # Push up the cookbooks
                deployment_cookbooks = os.path.join(os.path.dirname(deployment.__file__), "cookbooks")
                put(local_path=deployment_cookbooks, remote_path=project_dir)
                # Write the template files out to cookbooks/deployment/templates/default dir on the server
                deployment_module_path = os.path.dirname(deployment.__file__)
                deployment_template_dir = os.path.join(deployment_module_path, "templates", "deployment")
                print("Uploading deployment templates")
                for template_name in os.listdir(deployment_template_dir):
                    if os.path.isdir("%s/%s" % (deployment_template_dir, template_name)):
                        continue
                    print("Uploading %s" % template_name)
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
                        if not exists(cookbook):
                            print("Downloading cookbook: %s" % cookbook)
                            run("knife cookbook site download %s" % cookbook)
                            # extract this cookbook
                            zipped_cookbook = run("ls | egrep '%s\-[0-9\.]+\.tar\.gz'" % cookbook).split()[0]
                            print("Extracting %s" % zipped_cookbook)
                            run("tar xf %s" % zipped_cookbook, quiet=True)
                    with cd("deployment/recipes"):
                        print("Uploading recipes from DEPLOY_EXTRA_RECIPES")
                        extra_recipes = getattr(django_settings, "DEPLOY_EXTRA_RECIPES", [])
                        for extra_recipe in extra_recipes:
                            template_context = Context({})
                            template_contents = StringIO(get_template(extra_recipe).render(template_context))
                            template_name = os.path.split(extra_recipe)[1]
                            put(local_path=template_contents, 
                                remote_path=os.path.join(
                                        project_dir, 'cookbooks', 'deployment', 
                                        'recipes', template_name
                                    )
                                )
        # Run Chef as root
        with cd(project_dir):
            sudo("chef-solo -c solo.rb -j solo.json")
        sudo("chown %s:%s -R %s" % (username, username, deploy_dir))


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
        "yum",
        "yum-epel",
    ]
    cookbooks.extend(getattr(django_settings, "DEPLOY_COOKBOOKS", []))
    return cookbooks


def initialize_config():
    from django.conf import settings as django_settings
    if not DEPLOY_CONFIG:
        DEPLOY_CONFIG.update(DEPLOY_CONFIG_DEFAULT)
        username = getattr(django_settings, "DEPLOY_USERNAME", "ubuntu")
        password = getattr(django_settings, "DEPLOY_PASSWORD", "ubuntu")
        home_dir = getattr(django_settings, "DEPLOY_HOME_DIR", 
            "/home/%s" % username
        )
        ssh_dir = "/root/.ssh"
        deploy_dir = getattr(django_settings, 
            "DEPLOY_DEPLOY_DIR",
            "%s/web" % home_dir
        )
        git_branch = getattr(django_settings, "DEPLOY_GIT_BRANCH", "master")
        repository = getattr(settings, 
            "DEPLOY_GIT_REPOSITORY", 
            local("git config --get remote.origin.url", 
            capture=True))
        project_name = os.path.splitext(repository.split("/")[-1])[0]
        project_dir = "%s/%s" % (deploy_dir, project_name)
        main_app_name = getattr(django_settings, 
            "DEPLOY_MAIN_APP_NAME", 
            project_name
        )
        main_app_dir = getattr(django_settings, 
            "DEPLOY_MAIN_APP_DIR",
            "%s/%s" % (project_dir, main_app_name)
        )
        site_url = getattr(django_settings, "SITE_URL", "http://localhost")
        setting_overrides = {
            "project" : {
                "deployment" : {
                    "username" : username,
                    "password" : password,
                    "home_dir" : home_dir,
                    "main_app_name" : main_app_name,
                    "main_app_dir" : main_app_dir,
                    "ssh_dir" : ssh_dir,
                    "deploy_dir" : deploy_dir,
                    "project_dir" : project_dir,
                    "git_repository" : repository,
                    "git_branch" : git_branch,
                    "project_name" : project_name,
                    "site_url" : site_url
                }
            }
        }
        print(setting_overrides)
        DEPLOY_CONFIG.update(dict_merge(setting_overrides, DEPLOY_CONFIG))
        if hasattr(django_settings, "DEPLOY_CONFIG"):
            DEPLOY_CONFIG.update(dict_merge(django_settings.DEPLOY_CONFIG,
                DEPLOY_CONFIG))


def get_config(*args):
    """ Gets the configuration for solo.json file. Supply arguments to get
        nested variables. So for example, we can say:
        get_config("project", "deployment", "project_dir")
    """
    initialize_config()
    if not args:
        return DEPLOY_CONFIG
    else:
        val = DEPLOY_CONFIG
        for arg in args:
            val = val.get(arg)
        return val

def add_config(config, override=True):
    """ Adds configuration for solo.json 
    """
    current_config = get_config()
    if override:
        current_config.update(dict_merge(config, current_config))
    else:
        dict_merge(current_config, config)


def get_solo_json():
    """ Return the JSON for the solo.json file
    """
    output = json.dumps(get_config())
    return output

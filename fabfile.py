from StringIO import StringIO
import os

from fabric.api import (
    cd, settings, local, run, sudo, env, put
)

import deployment

solo_rb = """
root = "%s"
file_cache_path root
cookbook_path root + '/cookbooks'
"""

solo_json = """
{
    "run_list": [ "recipe[deployment::default]" ]
}
"""

def deploy():
    """ Deploys the Django application
    """
    print("Deploying Django application")
    with settings(warn_only=True):
        # make sure we have a SSH key
        if run("test -f ~/.ssh/id_rsa.pub").failed:
            run('ssh-keygen -q -t rsa -f ~/.ssh/id_rsa -N ""', quiet=True)
            result = run("cat ~/.ssh/id_rsa.pub")
            run('echo -e "Host bitbucket.org\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config', quiet=True)
            
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
        # TODO: Get project_dir dynamically
        project_dir = "/root/jcfa"
        # TODO: Get repo_url dynamically
        repo_url = local("git config --get remote.origin.url", capture=True)
        print("The repo is: %s" % repo_url)
        if run("test -d %s" % project_dir).failed:
            with cd("~"):
                run("git clone %s" % repo_url)
        with cd(project_dir):
            print("Pulling the latest code")
            run("git pull")
            run("git checkout develop")
            run("git pull")
            # Run chef
            # Setup solo.rb
            solo_rb_contents = StringIO(solo_rb % project_dir)
            put(local_path=solo_rb_contents, remote_path="%s/solo.rb" % project_dir)
            solo_json_contents = StringIO(solo_json)
            put(local_path=solo_json_contents, remote_path="%s/solo.json" % project_dir)
            # Push up the cookbooks
            deployment_cookbooks = os.path.join(os.path.dirname(deployment.__file__), "..", "cookbooks")
            put(local_path=deployment_cookbooks, remote_path=project_dir)
            run("chef-solo -c solo.rb -j solo.json")

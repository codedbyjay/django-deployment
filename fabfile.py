from fabric.api import cd, settings


def deploy():
    """ Deploys the Django application
    """
    print("Deploying Django application")
    with settings(warn_only=True):
        if run("chef --version").failed:
            print("Installing ChefDK")
            with cd("/tmp/"):
            sudo("wget https://opscode-omnibus-packages.s3.amazonaws.com/ubuntu/12.04/x86_64/chefdk_0.5.1-1_amd64.deb")
            sudo("dpkg -i chefdk_0.5.1-1_amd64.deb")
            sudo("rm chefdk_0.5.1-1_amd64.deb")
    project_dir = "~"
    with cd(project_dir):
        
    

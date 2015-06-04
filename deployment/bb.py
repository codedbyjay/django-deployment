from bitbucket.bitbucket import Bitbucket

from deployment.utils import red_text

def get_bitbucket():
    from django.conf import settings as django_settings
    from deployment.fabfile import get_config
    username = get_config("bitbucket", "username")
    client_key = get_config("bitbucket", "client_key")
    client_secret = get_config("bitbucket", "client_secret")
    token = get_config("bitbucket", "access_token")
    token_secret = get_config("bitbucket", "access_token_secret")
    if not all([username, client_key, client_secret, token, token_secret]):
        return None
    bb = Bitbucket(username)
    bb.authorize(
        client_key,
        client_secret,
        'http://localhost/',
        token,
        token_secret
    )
    return bb


def deploy_key_exists(ssh_key, project_name=None):
    bb = get_bitbucket()
    if not bb:
        return False
    succ, keys = bb.deploy_key.all(project_name)
    if not succ:
        return False
    for key in keys:
        if key["key"] == ssh_key:
            return True
    return False

def add_deploy_key(ssh_key, project_name=None, label=None):
    if not deploy_key_exists(ssh_key, project_name=project_name):
        bb = get_bitbucket()
        if not bb:
            print(red_text("WARNING: Could not add deploy key for BitBucket project"))
            return
        result = bb.deploy_key.create(project_name, key=ssh_key, label=label)

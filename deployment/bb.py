from bitbucket.bitbucket import Bitbucket

from deployment.utils import red_text

def get_bitbucket():
    from django.conf import settings as django_settings
    username = getattr(django_settings, "DEPLOY_BITBUCKET_USERNAME", None)
    client_key = getattr(django_settings, "DEPLOY_BITBUCKET_CLIENT_KEY", None)
    client_secret = getattr(django_settings, "DEPLOY_BITBUCKET_CLIENT_SECRET", None)
    token = getattr(django_settings, "DEPLOY_BITBUCKET_ACCESS_TOKEN", None)
    token_secret = getattr(django_settings, "DEPLOY_BITBUCKET_ACCESS_TOKEN_SECRET", None)
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

# django-deployment
Use Fabric and Chef-Solo to manage deployment

Start by defining the information for your server. You can do this perhaps in local_settings.py or settings.py.


from fabric.api import env
env.hosts = ["server_ip"]
env.user = "user"
env.password = "password"

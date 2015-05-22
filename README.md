# django-deployment
Use Fabric and Chef-Solo to manage deployment

Start by defining the information for your server. You can do this perhaps in local_settings.py or settings.py.


from fabric.api import env
env.hosts = ["server_ip"]
env.user = "user"
env.password = "password"

There are a bunch of templates that can be overriden to configure deployment. During the deployment process,
these files are generated and sent up to the server, so Chef can use them. We use Django inheritance, so 
any changes you make will be picked up.

* deployment/local_settings.py.erb
* deployment/logrotate.erb
* deployment/nginx.conf.erb
* deployment/run_celery.sh.erb
* deployment/run_gunicorn.sh.erb
* deployment/upstart_celery.conf.erb
* deployment/upstart_gunicorn.conf.erb


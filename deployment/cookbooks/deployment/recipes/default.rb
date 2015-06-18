#
# Cookbook Name:: deployment
# Recipe:: default
#
# Copyright (c) 2015 The Authors, All Rights Reserved.
include_recipe "python"
include_recipe "apt"
include_recipe "yum"

deploy_dir = node["project"]["deployment"]["deploy_dir"]
project_dir = node["project"]["deployment"]["project_dir"]
project_name = node["project"]["deployment"]["project_name"]
username = node["project"]["deployment"]["username"]
main_app_dir = node["project"]["deployment"]["main_app_dir"]
main_app_name = node["project"]["deployment"]["main_app_name"]
server_name = node["project"]["deployment"]["server_name"]
gunicorn_port = 8000

# Stop service if it exists
service project_name do
    action :stop
    ignore_failure true
end



# Install our packages
packages = node["project"]["deployment"]["apt_packages"]
for package in packages do 
    apt_package package do
        action :install
    end
end

# Create the virtual env
python_virtualenv project_dir do
  owner username
  group username
  action :create
end

python_pip "--upgrade pip" do
  virtualenv project_dir
end

if File.exist?("#{project_dir}/requirements.txt")
    python_pip "-r #{project_dir}/requirements.txt" do
        virtualenv project_dir
    end
end

# Setup local settings, syncdb and collectstatic
template "#{main_app_dir}/local_settings.py" do
    source "local_settings.py.erb"
    action :create
    variables({
        :database_name => node["project"]["database"]["name"],
        :database_user => node["project"]["database"]["username"],
        :database_password => node["project"]["database"]["password"],
        :database_host => node["project"]["database"]["host"],
        :database_port => node["project"]["database"]["port"],
        :database_engine => node["project"]["database"]["engine"],
        :site_url => node["project"]["database"]["site_url"],
    })
end

commands = node["project"]["django"]["commands"]
for command in commands do
    bash "Run manage.py #{command}" do
        code <<-EOH
        cd #{project_dir}
        source bin/activate
        python manage.py #{command}
        EOH
    end
end

# Load initial data
initial_datas = node["project"]["django"]["initial_data"]
for initial_data in initial_datas do
    bash "Run manage.py loaddata #{initial_data}" do
        code <<-EOH
        cd #{project_dir}
        source bin/activate
        python manage.py #{initial_data}
        EOH
    end
end

# Setup Gunicorn script
template "#{project_dir}/bin/run_gunicorn.sh" do
    source "run_gunicorn.sh.erb"
    action :create
    mode "555"
    variables({
        :project_dir => project_dir,
        :username => username,
        :project_name => project_name,
        :main_app_name => main_app_name
        })
end 

# Setup upstart for gunicorn
template "/etc/init/#{project_name}.conf" do
    source "upstart_gunicorn.conf.erb"
    action :create
    variables({
        :project_dir => project_dir
        })
end

link "/etc/init.d/#{project_name}" do
  to "/lib/init/upstart-job"
end

# Setup nginx conf
service "nginx" do
    action :stop
    ignore_failure true
end

# remove some default config files
config_files = ["/etc/nginx/sites-available/default", 
    "/etc/nginx/sites-enabled/default"]

for config_file in config_files do 
    file config_file do
        action :delete
        ignore_failure 
    end
end

template "/etc/nginx/sites-available/#{project_name}" do
    source "nginx.conf.erb"
    action :create
    variables({
        :project_dir => project_dir,
        :server_name => server_name,
        :gunicorn_port => gunicorn_port
        })
end

link "/etc/nginx/sites-enabled/#{project_name}" do
  to "/etc/nginx/sites-available/#{project_name}"
end

# Restart postgres
service "postgresql" do
    action :restart
    ignore_failure true
end

# Create a logs dir
directory "#{project_dir}/logs" do
    action :create
end

service "nginx" do
    action :start
end

# Stop service if it exists
service project_name do
    action :start
end


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
    python_pip "--exists-action=w -r #{project_dir}/requirements.txt" do
        virtualenv project_dir
    end
end

# Setup local settings, syncdb and collectstatic
template "#{main_app_dir}/local_settings.py" do
    source "local_settings.py.erb"
    action :create
    variables({
        :database_name => node["project"]["deployment"]["database_name"],
        :database_user => node["project"]["deployment"]["database_user"],
        :database_password => node["project"]["deployment"]["database_password"],
        :database_host => node["project"]["deployment"]["database_host"],
        :database_port => node["project"]["deployment"]["database_port"],
        :site_url => node["project"]["deployment"]["site_url"],
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

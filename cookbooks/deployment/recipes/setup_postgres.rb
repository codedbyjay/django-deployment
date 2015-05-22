#
# Cookbook Name:: deployment::setup_postgres
# Recipe:: default
#
# Copyright (c) 2015 Jean-Mark Wright, All Rights Reserved.
print "Setting us PostgreSQL"

#include_recipe "database::postgres"
include_recipe "postgresql::apt_pgdg_postgresql"
include_recipe "postgresql::server"
include_recipe "postgresql::client"
include_recipe "postgresql::contrib"

db_user = node["project"]["database"]["username"]
db_password = node["project"]["database"]["password"]
db_name = node["project"]["database"]["database"]


def psql(cmd)
    execute "Psql: #{cmd}" do
        user "postgres"
        command "psql -c \"#{cmd}\""
        ignore_failure true
    end
end

def psqldb(cmd, database)
    execute "Psql: #{cmd}" do
        user "postgres"
        command "psql -c \"#{cmd}\" #{database}"
        ignore_failure true
    end
end

# Create the users and create the database
psql("CREATE USER #{db_user} WITH PASSWORD '#{db_password}'")
psql("CREATE DATABASE #{db_name} WITH OWNER #{db_user}")
psqldb("CREATE EXTENSION postgis", db_name)


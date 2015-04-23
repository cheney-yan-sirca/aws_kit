# 
https://confluence.sirca.org.au/confluence/display/SIRPROC/Setting+up+your+AWS+shell


# Installation Steps

## Option1: Start up a new instance and prepare the tools. 

If you already have an instance, just use next option.

1  edit env.sh for the configurations of creating a new development instance in aws.
2  run ./initiate_instance.sh. Note: this script might need root access. 

## Option2: Run this tool on an existing instance:

1  SCP all the files under files directory into the instance's home directory
2  Login to the instance and execute `sudo bash softwares.sh`


# Configurations
1  env.sh: config this file to run 
2  files/env.json: config this file for your own environments.


# some readings:

## key bindings of tmux:
files/tmux_guide.txt



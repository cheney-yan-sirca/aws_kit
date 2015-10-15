#!/usr/bin/env python
import json, yaml
import os, platform
import re
import cli.log
import ConfigParser, io

TARGET_LAYOUT_DIR = '~/.tmuxinator'
TARGET_ENV_DIR = '/var/tmp/tmux-session-config'
boto_config_template = ConfigParser.ConfigParser(allow_no_value=True)

boto_config_template.readfp(io.BytesIO("""[Credentials]
aws_access_key_id = <%aws_access_key_id%>
aws_secret_access_key = <%aws_secret_access_key%>
region = <%region%>

[Boto]
is_secure = True
https_validate_certificates = False
http_socket_timeout=100
aws_access_key_id = <%aws_access_key_id%>
aws_secret_access_key = <%aws_secret_access_key%>
region = <%region%>

[Sirca]
sirca_aws_region = <%region%>
sirca_product = xxxx
sirca_subsystem=loader
sirca_role=dev
sirca_project = xxxx
sirca_username = cyan


[DynamoDB]
region = <%region%> 
[DB]
region = <%region%> 
[Trac]
region = <%region%> 
[EBS]
region = <%region%> 
[s3]
region = <%region%> 
[Instance]
region = <%region%> 
[MySQL]
region = <%region%> 
[Pyami]
region = <%region%> 
[SDB]
region = <%region%> 
[SWF]
region = <%region%> 

    """))

aws_config_repeat_template = ConfigParser.ConfigParser(allow_no_value=True)

aws_config_repeat_template.readfp(io.BytesIO("""[profile <%aws_profile%>]
region = <%region%>
"""))
aws_credential_repeat_template = ConfigParser.ConfigParser(allow_no_value=True)

aws_credential_repeat_template.readfp(io.BytesIO("""[<%aws_profile%>]
aws_access_key_id = <%aws_access_key_id%>
aws_secret_access_key = <%aws_secret_access_key%>
"""))

templates = {
    "boto_config_template": boto_config_template,
    "aws_credential_repeat_template": aws_credential_repeat_template,
    "aws_config_repeat_template": aws_config_repeat_template
}


def replace_variables(possible_variable, variables):
    for key, value in variables.items():
        possible_variable = possible_variable.replace("<%{0}%>".format(key), value)
    return possible_variable


all_aws_config_content = []
all_aws_credentials_content = []

for path_name in [TARGET_LAYOUT_DIR, TARGET_ENV_DIR]:
    path_name = os.path.expanduser(path_name)
    if not os.path.exists(path_name):
        os.makedirs(path_name)


def prepare_global_aws_files(app, config, files_contained_path=TARGET_ENV_DIR, aws_credential_file='~/.aws/credentials',
                             aws_config_file="~/.aws/config"):
    shaped_vars = {}
    for value in config.values():
        variables = value['variables']
        path_name = os.path.join(os.path.expanduser(files_contained_path), variables['aws_profile'])
        if not os.path.exists(path_name):
            os.makedirs(path_name)
        vars = value['vars']  # this goes to environmental file

        for var, var_val in vars.items():
            shaped_vars[replace_variables(var, variables)] = replace_variables(var_val, variables)

        for file in value['files']:
            file_path = os.path.join(path_name, file['file_name'])
            if 'var' in file:  # this needs to go into variable
                shaped_vars[replace_variables(file['var'], variables)] = file_path
            if 'content' in file:
                with open(file_path, 'wb') as f:
                    file_content = replace_variables(file['content'], variables)
                    f.write(file_content)
            elif 'content_template' in file:
                template = templates[file['content_template']]
                target_ini = ConfigParser.RawConfigParser()
                for sect in template.sections():
                    new_sect_name = replace_variables(sect, variables)
                    target_ini.add_section(new_sect_name)
                    for item in template.items(sect):
                        key = item[0]
                        value = item[1] if item[1] else "NONE"
                        app.log.debug("processing variable %s:%s" % (replace_variables(key, variables),
                                                                     replace_variables(value, variables)))
                        target_ini.set(new_sect_name,
                                       replace_variables(key, variables),
                                       replace_variables(value, variables))
                with open(file_path, 'wb') as f:
                    target_ini.write(f)
            if 'mod' in file:
                os.chmod(file_path, int(file['mod'], 8))
        for repeated_template, pool in {aws_credential_repeat_template: all_aws_credentials_content,
                                        aws_config_repeat_template: all_aws_config_content}.items():
            appearance = ConfigParser.RawConfigParser()
            for sect in repeated_template.sections():
                new_sect_name = replace_variables(sect, variables)
                appearance.add_section(new_sect_name)
                for item in repeated_template.items(sect):
                    key = item[0]
                    value = item[1] if item[1] else "NONE"
                    appearance.set(new_sect_name,
                                   replace_variables(key, variables),
                                   replace_variables(value, variables))
            pool.append(appearance)
        with open(os.path.join(path_name, 'source-file'), 'wb') as f:
            for k, v in shaped_vars.items():
                f.write('export %s=%s' % (k, v))
                f.write("\n")

        prepare_tmux_layout(app, variables['aws_profile'], target_dir=os.path.expanduser(TARGET_LAYOUT_DIR))

    with open(os.path.expanduser(aws_credential_file), 'wb') as f:
        for x in all_aws_credentials_content:
            x.write(f)

    with open(os.path.expanduser(aws_config_file), 'wb') as f:
        for x in all_aws_config_content:
            x.write(f)


@cli.log.LoggingApp
def prepare_env(app):
    app.log.debug("Generating aws working environment from %s", app.params.config)
    config = json.load(open(os.path.join(os.path.dirname(__file__), app.params.config)))
    prepare_global_aws_files(app, config)


def prepare_tmux_layout(app, name, target_dir):
    try:
        app.log.debug("Generating tmux layout for %s", name)
        try:
            os.stat(target_dir)
        except:
            os.makedirs(target_dir)

        with open(os.path.join(target_dir, '%s.yml' % name), 'w') as f:
            layout = {'windows': [{'local': {'pre': None,
                                             'panes': [None],
                                             'layout': 'main-vertical'}}], 'root': '~/work/',
                      'name': str(name)}
            yaml.dump(layout, f)
            f.close()
    except StandardError as e:
        app.log.error("Failed to create yaml layout for %s, %s", name, e)


prepare_env.add_param("-c", "--config", help="the config file", default="env.json", type=str)

if __name__ == "__main__":
    prepare_env.run()

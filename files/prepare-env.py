#!/usr/bin/env python
import ConfigParser
import datetime
import io
import json
import os

import cli.log
import yaml

TARGET_LAYOUT_DIR =  os.path.expanduser('~/.tmuxinator')
TARGET_ENV_DIR = os.path.join(TARGET_LAYOUT_DIR, 'tmux-session-config')

aws_credential_repeat_template = ConfigParser.ConfigParser(allow_no_value=True)

aws_credential_repeat_template.readfp(io.BytesIO("""[<%aws_profile%>]
aws_access_key_id = <%aws_access_key_id%>
aws_secret_access_key = <%aws_secret_access_key%>
role_arn=<%role_arn%>
source_profile=<%source_profile%>
region = <%region%>

"""))

templates = {
    "aws_credential_repeat_template": aws_credential_repeat_template,
}

def replace_variables(possible_variable, variables):
    for key, value in variables.items():
        possible_variable = possible_variable.replace("<%{0}%>".format(key), value)
    return possible_variable


all_aws_config_content = []
all_aws_credentials_content = []

for path_name in [TARGET_LAYOUT_DIR, TARGET_ENV_DIR]:
    if not os.path.exists(path_name):
        os.makedirs(path_name)


def prepare_global_aws_files(app, config, files_contained_path=TARGET_ENV_DIR, aws_credential_file='~/.aws/credentials',
                             ):
    aws_credential_file = os.path.expanduser(aws_credential_file)
    shaped_vars = {}
    for value in config.values():
        variables = value['variables']
        path_name = os.path.join(files_contained_path, variables['aws_profile'])
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
                if isinstance(file['content'], list):
                    file['content'] = '\n'.join(file['content'])
            elif "from" in file:
                from_file_path=os.path.expanduser(file['from'])
                if not os.path.isfile(from_file_path):
                    raise ValueError("Failed to find source file %s" % from_file_path)
                file['content']=open(from_file_path).read()
            else:
                raise ValueError("Must provide either 'content' or file source('from') for a file. ")
            with open(file_path, 'wb') as f:
                    file_content = replace_variables(file['content'], variables)
                    f.write(file_content)
            if 'mod' in file:
                os.chmod(file_path, int(file['mod'], 8))
        for repeated_template, pool in {aws_credential_repeat_template: all_aws_credentials_content,
                                        }.items():
            one_profile = ConfigParser.RawConfigParser()
            for sect in repeated_template.sections():
                new_sect_name = replace_variables(sect, variables)
                one_profile.add_section(new_sect_name)
                for item in repeated_template.items(sect):
                    key = replace_variables(item[0], variables)
                    value = replace_variables(item[1] if item[1] else "NONE", variables)
                    if not key.startswith('<%') and not value.startswith('<%'):
                        one_profile.set(new_sect_name, key, value)
            all_aws_credentials_content.append(one_profile)

        with open(os.path.join(path_name, 'source-file'), 'wb') as f:
            for k, v in shaped_vars.items():
                f.write('export %s=%s' % (k, v))
                f.write("\n")

        prepare_tmux_layout(app, variables['aws_profile'], target_dir=os.path.expanduser(TARGET_LAYOUT_DIR))
    if os.path.isfile(aws_credential_file):
        # backup the file
        backup_file = '%s.backup.%s'%(aws_credential_file, datetime.datetime.now().isoformat())
        os.rename(aws_credential_file, backup_file)
    if not os.path.exists(os.path.dirname(aws_credential_file)):
        os.makedirs(os.path.dirname(aws_credential_file))
    with open(aws_credential_file, 'wb') as f:
        for x in all_aws_credentials_content:
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

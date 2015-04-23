#!/usr/bin/env python
import json, yaml
import os, platform
import cli.log

TARGET_LAYOUT_DIR = '~/.tmuxinator'
TARGET_ENV_DIR = '/var/tmp/tmux-session-config'

templates = {
    "BOTO_CONFIG": """[Credentials]
aws_access_key_id = xxxx
aws_secret_access_key = xxxx
region = xxxx

[Boto]
is_secure = True
https_validate_certificates = False
http_socket_timeout=100
aws_access_key_id = xxxx
aws_secret_access_key = xxxx
region = xxxx

[Sirca]
sirca_aws_region = xxxx
sirca_product = xxxx
sirca_subsystem=loader
sirca_role=dev
sirca_project = xxxx
sirca_username = cyan


[DynamoDB]
region = ap-southeast-2
    """,
    "AWS_CONFIG_FILE": """[default]
aws_access_key_id = xxxx
aws_secret_access_key = xxxx
region = xxxx

    """,
    "source_file": """export BOTO_CONFIG=xxxx
export AWS_CONFIG_FILE=xxxx
export SSH_KEY_FILE=xxxx
export PAPERTRAIL_API_TOKEN=xxxx
"""

}


@cli.log.LoggingApp
def prepare_env(app):
    app.log.debug("Generating aws working environment from %s", app.params.config)
    config = json.load(open(os.path.join(os.path.dirname(__file__), app.params.config)))

    if app.params.cmd == 'init-layout':
        for _, value in config.items():
            key = '%s_%s_%s' % (value['project'], value['profile'], value['region_name'])
            prepare_tmux_layout(app, key, target_dir=os.path.expanduser(TARGET_LAYOUT_DIR))
    else:
        for _, value in config.items():
            key = '%s_%s_%s' % (value['project'], value['profile'], value['region_name'])
            if key == app.params.cmd:
                prepare_aws_env(app, app.params.cmd, value, target_dir=os.path.expanduser(TARGET_ENV_DIR))
                exit(0)
        app.log.error("Failed to find an configuration for %s. Nothing is done.", app.params.cmd)

def prepare_tmux_layout(app, name, target_dir):
    try:
        app.log.debug("Generating tmux layout for %s", name)
        try:
            os.stat(target_dir)
        except:
            os.makedirs(target_dir)

        with open(os.path.join(target_dir, '%s.yml' % name), 'w') as f:
            layout = {'windows': [{'local': {'pre': None,
                                             'panes': [
                                                 "%s %s %s" % ("python",
                                                               os.path.join(target_dir, os.path.basename(__file__)),
                                                               "$(tmux list-panes -F '#{session_name} #{pane_active}' | grep -E ' 1$' | awk '{print $1}' | head -n 1)")
                                             ],
                                             'layout': 'main-vertical'}}], 'root': '~/work/',
                      'name': str(name)}
            yaml.dump(layout, f)
            f.close()
    except StandardError as e:
        app.log.error("Failed to create yaml layout for %s, %s", name, e)


def prepare_aws_env(app, name, value, target_dir):
    try:
        app.log.debug("Generating environmental file for %s", name)
        try:
            os.stat(os.path.join(target_dir, name))
        except:
            os.makedirs(os.path.join(target_dir, name))

        for file in value['contents']['env']['file']:
            file_name=file['file_name']
            content=file['content']
            key=file['key']
            with open(os.path.join(target_dir, name, file_name), 'w') as f:
                if content == "_FROM_TEMPLATE_":
                    template = templates[key]
                    for var, var_val in value['contents']['variables'].items():
                        template = template.replace('%s = xxxx' % var, '%s = %s' % (var, var_val))
                    f.writelines(template)
                else:
                    f.writelines(content)
                if key == "SSH_KEY_FILE":
                    os.chmod(os.path.join(target_dir, name, file_name), 0600)
                f.close()
        ## source file
        with open(os.path.join(target_dir, name, 'source-file'), "w") as f:
            template_string = templates['source_file']

            for file in value['contents']['env']['file']:
                var=file['key']
                file=file['file_name']
                template_string = template_string.replace('export %s=xxxx' % var,
                                                          'export %s=%s' % (var, os.path.join(target_dir, name, file)))
            for var, var_val in value['contents']['env']['content'].items():
                template_string = template_string.replace('export %s=xxxx' % var,
                                                          'export %s=%s' % (var, var_val))
            f.writelines(template_string)
            if not '.amzn1' in platform.uname()[2]:
                f.writelines('source ~/py26/bin/activate')
            f.close()
    except StandardError as e:
        app.log.error("Failed to create environment file for %s, %s", name, e)


prepare_env.add_param("-c", "--config", help="the config file", default="env.json", type=str)
prepare_env.add_param("cmd", help="The command to execute", type=str, default='init-layout')

if __name__ == "__main__":
    prepare_env.run()

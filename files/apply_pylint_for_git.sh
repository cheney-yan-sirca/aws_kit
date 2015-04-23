#!/usr/bin/env bash
echo "git-pylint-commit-hook --limit 8 --pylintrc ../python_common/pylintrc" >> .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit                                                                       

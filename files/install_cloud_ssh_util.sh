#!/usr/bin/env bash
cd /tmp
while [ ! -d /tmp/datasets ];
do
    git clone git@github.com:sirca/datasets
done
cd /tmp/datasets/test_framework/datasets_test_framework

sudo python setup.py install
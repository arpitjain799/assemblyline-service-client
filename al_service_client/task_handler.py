#!/usr/bin/env python

# Run a standalone AL service

import hashlib
import json
import logging
import os
import shutil
import tempfile
import time

import pyinotify
import yaml

from al_service_client import Client
from assemblyline.common import log

log.init_logging('assemblyline.task_handler', log_level=logging.INFO)
log = logging.getLogger('assemblyline.task_handler')

svc_api_host = os.environ['SERVICE_API_HOST']
# name = os.environ['SERVICE_PATH']

# svc_name = name.split(".")[-1].lower()

svc_client = Client(svc_api_host)

result_found = False


class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        global result_found
        if 'result.json' in event.pathname:
            result_found = True
        log.info(f'Creating: {event.pathname}')

    def process_IN_DELETE(self, event):
        log.info(f'Removing: {event.pathname}')


def done_task(task, result, task_hash):
    folder_path = os.path.join(tempfile.gettempdir(), task['service_name'].lower(), 'completed', task_hash)
    try:
        msg = svc_client.task.done_task(task=task, result=result)
        log.info('RESULT OF DONE_TASK:: '+msg)
    finally:
        if os.path.isdir(folder_path):
            shutil.rmtree(folder_path)


def get_classification(yml_classification=None):
    log.info('Getting classification definition...')

    if yml_classification is None:
        yml_classification = "/etc/assemblyline/classification.yml"

    # Get classification definition and save it
    classification = svc_client.help.get_classification_definition()
    with open(yml_classification, 'w') as fh:
        yaml.safe_dump(classification, fh)


def get_systems_constants(json_constants=None):
    log.info('Getting system constants...')

    if json_constants is None:
        json_constants = "/etc/assemblyline/constants.json"

        # Get system constants and save it
        constants = svc_client.help.get_systems_constants()
        with open(json_constants, 'w') as fh:
            json.dump(constants, fh)


def get_task():
    task = svc_client.task.get_task(service_name=service_config['SERVICE_NAME'],
                                    service_version=service_config['SERVICE_VERSION'],
                                    service_tool_version=service_config['TOOL_VERSION'],
                                    file_required=service_config['SERVICE_FILE_REQUIRED'])
    return task


def get_service_config(yml_config=None):
    if yml_config is None:
        yml_config = "/etc/assemblyline/service_config.yml"

    # Load from the yaml config
    while True:
        log.info('Trying to load service config YAML...')
        if os.path.exists(yml_config):
            with open(yml_config, 'r') as yml_fh:
                yaml_config = yaml.safe_load(yml_fh)
            return yaml_config
        else:
            time.sleep(5)


def task_handler():
    global result_found

    try:
        wm = pyinotify.WatchManager()  # Watch Manager
        mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE  # watched events

        notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
        notifier.start()

        while True:
            task = get_task()

            task_hash = hashlib.md5(str(task['sid'] + task['fileinfo']['sha256']).encode('utf-8')).hexdigest()
            folder_path = os.path.join(tempfile.gettempdir(), task['service_name'].lower(), 'completed', task_hash)
            if not os.path.isdir(folder_path):
                os.makedirs(folder_path)

            wdd = wm.add_watch(folder_path, mask, rec=False)

            while not result_found:
                #log.info(f'Waiting for result.json in: {folder_path}')
                time.sleep(0.1)

            result_found = False
            wm.rm_watch(list(wdd.values()))

            result_json_path = os.path.join(folder_path, 'result.json')
            with open(result_json_path, 'r') as f:
                result = json.load(f)
                log.info(str(result))
            done_task(task, result, task_hash)
    finally:
        notifier.stop()


if __name__ == '__main__':
    get_classification()
    get_systems_constants()
    service_config = get_service_config()
    task_handler()

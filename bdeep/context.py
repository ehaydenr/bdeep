"""
This module sets up the proper environment context for BDEEP python scripts.
"""

import os
import sys
import glob
import json
import pprint
import logging
import datetime
import logging

config = {}

def getHeaderString():
    firstLine = "{0} JOB STARTED {1} {0}".format("*"*40, datetime.datetime.utcnow())
    configuration = pprint.pformat(config)
    lastLine = "-- OUTPUT BELOW --"
    return "\n{0}\n{1}\n{2}\n".format(firstLine, configuration, lastLine)

"""
Environment variables should override configuration files
"""
def resolveConfig(base):

    global config

    if base is None:
        base = {}

    config = base

    # Set environment if exists
    env = os.environ.get('BDEEP_RUN_ENV')
    if env is not None:
        config["environment"] = env

    # Set inputRoot if exists
    inputRoot = os.environ.get('BDEEP_RUN_INPUT_ROOT')
    if inputRoot is not None:
        config["inputRoot"] = inputRoot

    # Set outputRoot if exists
    outputRoot = os.environ.get('BDEEP_RUN_OUTPUT_ROOT')
    if outputRoot is not None:
        config["outputRoot"] = outputRoot

    # Set logging if exists
    loggingRoot = os.environ.get('BDEEP_RUN_LOGGING_ROOT')
    if loggingRoot is not None:
        config["loggingRoot"] = loggingRoot

    name = os.environ.get('BDEEP_RUN_NAME')
    if name is not None:
        config["name"] = name

    handler = logging.StreamHandler(sys.stdout)

    if "loggingRoot" in config and "name" in config:
        logDir = os.path.join(config["loggingRoot"], config["environment"])

	if not os.path.exists(logDir):
	    os.makedirs(logDir)

	logFile = os.path.join(logDir, "{0}.log".format(config["name"]))
        handler = logging.FileHandler(logFile)
    else:
        handler = logging.StreamHandler(sys.stdout)

    log = logging.getLogger("BDEEP")
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    log.debug(getHeaderString())

# Bring in Config if exists
configs = glob.glob("bdeep_config_*.json")
if len(configs) > 1:
    assert False, "Too many configuration files matching 'bdeep_config_*.json'"
if len(configs) == 1:
    with open(configs[0], 'r') as f:
        resolveConfig(json.load(f))

""" Client API """

def generateInputPath(pathStr):
    return os.path.join(config["inputRoot"], pathStr)

def generateOutputPath(pathStr):
    return os.path.join(config["outputRoot"], pathStr)

def getJobArgs():
    return config["args"]

def generateProjectPath(pathStr):
    return os.path.join(config["mainPath"], pathStr)

def getConfig():
    return config

def setConfig(cfg):
    resolveConfig(cfg)

def loadConfig(path):
    with open(path, 'r') as f:
        resolveConfig(json.load(f))

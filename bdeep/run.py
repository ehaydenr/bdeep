import argparse
from bdeep import context
import importlib
import os
import json
import pip
import logging

parser = argparse.ArgumentParser(description='Run a BDEEP Job')
parser.add_argument('main', type=str, help='Path to directory with manifest.json')
parser.add_argument('mode', type=str, help='Context to run the job in. (e.g. DEV, PROD)')

args = parser.parse_args()

# Read Manifest
manifestPath = os.path.join(args.main, 'manifest.json')
manifest = None
try:
    with open(manifestPath, 'r') as f:
        manifest = json.load(f)
except Exception as error:
    print error
    assert False, "Manifest doesn't exist"

mainScript = os.path.join(args.main, manifest['main'])
requirements = os.path.abspath(os.path.join(args.main, manifest['requirements']))
config = manifest[args.mode]['config']
config["mainPath"] = args.main
config["environment"] = args.mode
config["name"] = manifest['name']

# Setup logging
if "logging" in manifest and "name" in manifest:

	logRoot = manifest["logging"]["root"]
	logDir = os.path.join(logRoot, args.mode)

	if not os.path.exists(logDir):
	    os.makedirs(logDir)

	logFile = os.path.join(logDir, "{0}.log".format(manifest["name"]))
	config["logging"] = {
		"file": logFile,
		"level": logging.DEBUG
	}


# Make sure packages are installed
pip.main(["install", "-q", "-r", requirements])

# Force config
context.setConfig(config)
execfile(os.path.abspath(mainScript))

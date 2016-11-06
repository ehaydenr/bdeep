import argparse
import json
import os
import errno
import git
from docker import Client
import shutil
import jinja2

parser = argparse.ArgumentParser(description='Run a BDEEP Job')
parser.add_argument('jobsfile', type=str, help='Path to jobs.json')

args = parser.parse_args()

try:
    with open(args.jobsfile, 'r') as f:
        jobs = json.load(f)
except Exception as error:
    print error
    assert False, "Bad jobs file."

print jobs

dockercli = Client(base_url='unix://var/run/docker.sock', version='auto')

def writeFile(path, contents):
    try:
        with open(path, 'w') as f:
            f.write(contents)
    except Exception as error:
        print error
        assert False, 'Error writing to file'

def makePath(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def cloneRepo(destPath, remote, branch):
    makePath(destPath)
    repo = git.Repo.init(destPath)
    origin = repo.create_remote('origin', remote)
    origin.fetch()


    repo.create_head(branch, origin.refs[branch])
    repo.heads[branch].set_tracking_branch(origin.refs[branch])
    repo.heads[branch].checkout()
    origin.pull()

'''
Verify that the proper remote and branch are set.
'''
def verifyRepo(repoPath, remote, branch):
    repo = git.Repo(repoPath)

    if branch not in repo.heads:
        return False

    return not any([
        repo.head.ref != repo.heads[branch],
        repo.remotes.origin.url != remote
        ])

'''
Check if the repository has a newer version on remote
'''
def repoIsBehind(repoPath):
    repo = git.Repo(repoPath)
    repo.remotes.origin.fetch()
    commits_behind = repo.iter_commits('{0}..origin/{0}'.format(repo.active_branch.name))
    count = sum(1 for c in commits_behind)
    return count > 0

def repoExists(repoPath):
    return os.path.exists(os.path.join(repoPath, '.git'))

def updateRepo(repoPath):
    repo = git.Repo(repoPath)
    origin = repo.remotes.origin
    origin.pull()

def buildContainer(path, tag):
    print "Building %s" % path
    response = [line for line in dockercli.build(path=path, tag=tag)]
    print response

def getCrontabFilePath(job, mode):
    fileName = '{0}-{1}'.format(job, mode)
    return os.path.join('/etc/cron.d', fileName)


def updateCrontab(job, mode, schedule, user, command):
    line = '{0} {1} {2}'.format(schedule, user, command)

    path = getCrontabFilePath(job, mode)
    print "update crontab filepath: %s" % path
    writeFile(path, line)

def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)

def buildCommand(tag, dockerArgs):
    defaultArgs = ['-e BDEEP_RUN_LOGGING_ROOT=/var/log/bdeep', '-v /var/log/bdeep:/var/log/bdeep']
    args = defaultArgs + dockerArgs
    return 'docker run {0} {1}'.format(" ".join(args), tag)

projectsRoot = 'projects'
makePath(projectsRoot)

for job in jobs:
    for mode in job['modes']:

        jobPath = os.path.join(projectsRoot, mode['name'], job['name'])
        makePath(jobPath)

        remote = mode['remote']
        branch = mode['branch']
        tag = 'bdeep-{0}-{1}'.format(job['name'], mode['branch'])

        # If repo exists and is incorrect, just delete contents
        if repoExists(jobPath) and not verifyRepo(jobPath, remote, branch):
            print "Repo exists and is incorrect. Deleting: %s" % jobPath
            shutil.rmtree(jobPath)

        rootDir = os.path.join(jobPath, mode['rootDir'])

        # See if project needs updating
        if not repoExists(jobPath) or repoIsBehind(jobPath):
            print "Project needs updating"
            if not repoExists(jobPath):
                print "Repo didn't exist"
                cloneRepo(jobPath, mode['remote'], mode['branch'])
            elif repoIsBehind(jobPath):
                print "Repo was dirty"
                updateRepo(jobPath)

            print "Building..."

            buildContainer(rootDir, tag)

        command = buildCommand(tag, mode.get('dockerArgs') or [])

        if 'cronTpl' in mode:
            cronFile = os.path.join(rootDir, mode['cronTpl'])
            rendered = render(cronFile, {'command': command})
            path = getCrontabFilePath(job['name'], mode['name'])
            writeFile(path, rendered)
        else:
            # No way to know if the schedule has been updated. Go ahead and rewrite crontab
            cron = mode['cron']
            updateCrontab(job['name'], mode['name'], cron['schedule'], cron['user'], command)

        print "Done."

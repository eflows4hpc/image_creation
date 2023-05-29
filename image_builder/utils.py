import subprocess
import shutil
import os
import sys

def run_commands(commands, logger = None, check_error = False, **kwargs):
    cmd = ' && '.join(commands)
    res = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
    error = False
    for line in iter(res.stdout.readline, b''):
        if logger:
            line = line.decode("utf-8").strip()
            logger.info(line)
        else:
            line = line.decode(sys.stdout.encoding)
            sys.stdout.write(line) 
        if check_error:
            error = error or checkError(line)
    res.wait()
    if res.returncode != 0 :
        raise subprocess.CalledProcessError(res.returncode, res.args)
    if error:
        raise Exception("Error message in the execution")

def checkError(line):
    return "error:" in line.lower()



def ssh_run_commands(login_info, commands, key=None, **kwargs):
    cmd = ' && '.join(commands)
    if key is None:
        ssh_cmd = f"ssh {login_info} '{cmd}'"
    else:
        ssh_cmd = f"ssh -i {key} {login_info} '{cmd}'"
    res = subprocess.run(ssh_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    return res.stdout.decode()

def scp_to_remote(login_info, source, remote, **kwargs):
    res = subprocess.run(f"scp {source} {login_info}:{remote}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    return res.stdout.decode()

def scp_from_remote(login_info, source, remote, **kwargs):
    res = subprocess.run(f"scp {source} {login_info}:{remote}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    return res.stdout.decode()

def replace_in_file(source, destination, to_replace):
    f1 = open(source, 'r')
    f2 = open(destination, 'w')
    for line in f1:
        for key, value in to_replace.items():
            line = line.replace(key, value)
        f2.write(line)
    f1.close()
    f2.close()

def append_text_to_file(filepath, to_append):
    file = open(filepath, 'a')
    file.write(to_append)
    file.close()

def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)
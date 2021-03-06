#!/usr/bin/env python

# Check software versions on the target

__author__ = "Elphel"
__copyright__ = "Copyright 2016, Elphel, Inc."
__license__ = "GPL"
__version__ = "3.0+"
__maintainer__ = "Oleg K Dzhimiev"
__email__ = "oleg@elphel.com"
__status__ = "Development"

import json
import os
import subprocess
import sys
    
#http://stackoverflow.com/questions/287871/print-in-terminal-with-colors-using-python
class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[38;5;214m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  BOLDWHITE = '\033[1;37m'
  UNDERLINE = '\033[4m'

def shout(cmd):
  subprocess.call(cmd,shell=True)

def command_over_ssh(addr,command):
    cmd = "ssh "+addr+" "+command
    print("cmd: "+cmd)
    try:
      ret = subprocess.check_output(cmd,stderr=subprocess.STDOUT,shell=True)
    except subprocess.CalledProcessError:
      raise Exception("ssh to target requires access by public key. Run: \033[1;37mssh-copy-id "+addr+"\033[0m")
    return ret.strip() 

def read_local_conf(conf_file,pattern):
  ret = "0"
  if os.path.isfile(conf_file):
    with open(conf_file,"r") as f:
      lines = f.readlines()
      for line in lines:
        test = line.find(pattern)
        if test!=-1:
          ret = line.split("=")[1].strip().strip("\"")
  return ret

def get_versions_from_target(addr,tdir):
  # print remote package list
  tmp_str = command_over_ssh(addr,"'ls "+tdir+"'")
  
  remote_list = []
  
  tmp_list = tmp_str.split()
  for elem in tmp_list:
    remote_list.append([elem,command_over_ssh(addr,"'cat "+tdir+"/"+elem+"'")])
  
  return remote_list

def get_versions_from_target_quick(addr,tdir):
  # print remote package list
  ldir = os.path.basename(tdir)
  if os.path.isdir(ldir):
    shout("rm -rf "+ldir)
    
  shout("scp -r "+addr+":"+tdir+" .")
  
  remote_list = []
  
  for f in os.listdir(ldir):
    with open(ldir+"/"+f, 'r') as content_file:
      content = content_file.read()
    remote_list.append([f,content.strip()])
  
  shout("rm -rf "+ldir)
  
  return remote_list

def get_version_from_git(path,vfile):
  #print(path)
  cwd = os.getcwd()
  os.chdir(cwd+"/"+path)
  
  p0=""
  p1=""
  
  if os.path.isfile(vfile):
    #PE.PV
    
    f=open(vfile)
    for line in f:
      line = line.strip()
      if (line[0]!="#"):
            break  
    p0 = line
    #PR
    
    cmd = "git rev-list --count $(git log -1 --pretty=format:\"%H\" "+vfile+")..HEAD"
    p1 = subprocess.check_output(cmd,stderr=subprocess.STDOUT,shell=True)
    p1 = p1.strip()
        
  else:
    print(vfile+" file is missing in the project")
    
  os.chdir(cwd)
  return p0+"."+p1

def deep_analysis(local,remote):
  print("\nVersion analysis")
  
  print("\n"+bcolors.BOLDWHITE+"{:<24}".format("Project")+"{:<16}".format("Local GIT")+"{:<16}".format("Target Version")+bcolors.ENDC)
  
  update_list = ""
  for pl,vl in local:
    recstr = "{:<24}".format(pl)+"{:<16}".format(vl)
    prfound = False
    for pr,vr in remote:
      if pl==pr:
        prfound = True
        recstr = recstr+"{:<16}".format(vr)
        if vl==vr:
          recstr = bcolors.OKGREEN+recstr+bcolors.ENDC
        else:
          recstr = bcolors.FAIL+recstr+bcolors.ENDC
          pl = getname(pl,"","recipe_to_package")
          update_list = update_list+" bitbake "+pl+" -c target_scp -f\n"
    if not prfound:
      recstr = bcolors.WARNING+recstr+bcolors.ENDC
      pl = getname(pl,"","recipe_to_package")
      update_list = update_list+" bitbake "+pl+" -c target_scp -f\n"

    print(recstr)
  if not update_list=="":
    print("\nTo sync the software on the target run:\n"+update_list)

# all exceptions in one place
def getname(name,project,mode):
  global project_prefix
  global package_prefix
    
  if mode=="project_to_recipe":
    if name.find(project_prefix)==0:
      name = name[len(project_prefix):]

    if project.find(package_prefix)==0:
      name = package_prefix+name
      #only exception
    if name=="fpga-x393_sata":
      name="fpga-x393sata"
    return name
  
  elif mode=="recipe_to_package":
    if name=="linux-elphel":
      name = "linux-xlnx"
    elif name=="apps-php-extension":
      name = "php"
    return name
  else:
    return name

usage = """Usage example:
    {0}{1} root@192.168.0.9{2}, where
        192.168.0.9 - target ip address
        root        - target user
""".format(bcolors.BOLDWHITE,sys.argv[0],bcolors.ENDC)

# hardcoded
user = ""
ip = ""
local_conf = "poky/build/conf/local.conf"
target_dir = "/etc/elphel393/packages"
local_project_list = "projects.json"
local_dirs = ["rootfs-elphel","fpga-elphel","linux-elphel"]
git_vfile = "VERSION"
project_prefix = "elphel-"
package_prefix = "fpga-"

if len(sys.argv)>1:
  rootip = sys.argv[1].split("@")
  if len(rootip)>1:
    user,ip = rootip
  else:
    ip = rootip[0]
else:
  if (os.path.isfile(local_conf)):
    user   = read_local_conf(local_conf,"REMOTE_USER")
    ip = read_local_conf(local_conf,"REMOTE_IP")
    print(bcolors.WARNING+"NOTE: The default user and ip are taken from "+local_conf+bcolors.ENDC)
    print(bcolors.WARNING+"NOTE: To check against the latest code run ./setup.py first"+bcolors.ENDC)
    print(usage)
  
  if user=="" or ip=="":
    raise Exception(usage)

print("Software/firmware versions check for target "+bcolors.BOLDWHITE+user+"@"+ip+bcolors.ENDC)

print(bcolors.BOLDWHITE+"=== Read versions from the target ==="+bcolors.ENDC)
target_list = get_versions_from_target_quick(user+"@"+ip,target_dir)

#print(target_list)

print(bcolors.BOLDWHITE+"=== Read local versions ==="+bcolors.ENDC)
with open(local_project_list) as data_file:
  Projects = json.load(data_file)

local_list = []

for p,v in Projects.items():
  if p in local_dirs:
    if isinstance(v,dict):
      for k,l in v.items():
        tmp = get_version_from_git(p+"/"+k,git_vfile)
        name = getname(k,p,"project_to_recipe")
        local_list.append([name.encode('ascii','ignore'),tmp])
        
    elif isinstance(v,list):
      tmp = get_version_from_git(p,git_vfile)
      local_list.append([p.encode('ascii','ignore'),tmp])
    else:
      raise Exception("Unknown error")

#print(local_list)

deep_analysis(local_list,target_list)



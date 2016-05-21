#!/usr/bin/python

"""
Run a script in the background with a new group ID and a script which will kill the job and children.
"""

import sys,os,re,subprocess
regex_pop = '^%s=(.+)'
#try:
if 1:
	cmd_flag = sys.argv.pop([None!=re.match(regex_pop%'command',s) for s in sys.argv].index(True))
	cmd = re.match(regex_pop%'command',cmd_flag).group(1)
	name_flag = sys.argv.pop([None!=re.match(regex_pop%'name',s) for s in sys.argv].index(True))
	name = re.match(regex_pop%'name',name_flag).group(1)
	try:
		log_flag = sys.argv.pop([None!=re.match(regex_pop%'log',s) for s in sys.argv].index(True))
		errorlog = re.match(regex_pop%'log',log_flag).group(1)
	except: errorlog = 'log-backrun-%s'%name
	try:
		pre_flag = sys.argv.pop([None!=re.match(regex_pop%'pre',s) for s in sys.argv].index(True))
		precmd = re.match(regex_pop%'pre',pre_flag).group(1)+' && '
	except: precmd = ''
#except:
#	import pdb;pdb.set_trace()
#	print '[USAGE] \'./backrun.py name="<name>" command="<command>"\' (make sure you use double quotes)' 
#	print '[USAGE] runs a job in the background and gives you a killswitch'
#	sys.exit(1)

cmd_full = "%snohup %s > %s 2>&1 &"%(precmd,cmd,errorlog)
print '[BACKRUN] running "%s"'%cmd_full
job = subprocess.Popen(cmd_full,shell=True,cwd='./',preexec_fn=os.setsid)
ask = subprocess.Popen('ps xao pid,ppid,pgid,sid,comm',
	shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
ret = '\n'.join(ask.communicate()).split('\n')
pgid = next(int(i.split()[2]) for i in ret if re.match('^\s*%d\s'%job.pid,i))
kill_script = 'script-stop-%s.sh'%name
term_command = 'pkill -TERM -g %d'%pgid
with open(kill_script,'w') as fp: fp.write(term_command+'\n')
os.chmod(kill_script,0744)
job.communicate()

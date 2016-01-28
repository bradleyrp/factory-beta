
#---INTERFACE TO CONTROLLER
#-------------------------------------------------------------------------------------------------------------

#---filter and evaluate
RUN_ARGS_UNFILTER := $(wordlist 1,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
RUN_ARGS := $(filter-out banner run shutdown shell kickstart package bootstrap reset connect reconnect wipe devclean omninuke,$(RUN_ARGS_UNFILTER))
$(eval $(RUN_ARGS):;@:)

#---show the banner if no targets
banner:
	@sed -n 1,13p deploy/README.md
	@echo "[NOTE] use 'make help' for details"

#---do not target arguments if using python
.PHONY: banner ${RUN_ARGS}

#---start a server and detach the screen
run:
	@bash deploy/run.sh ${RUN_ARGS} || echo "[STATUS] fail"

#---reattach the screen running the server
shutdown:
	@bash deploy/shutdown.sh  || echo "[STATUS] fail"

#---activate the virtualenvironment and run the shell
shell: 
	@bash deploy/shell.sh ${RUN_ARGS} || echo "[STATUS] fail"

#---kickstart a new project with a simulator
kickstart: bootstrap
	@bash deploy/kickstart.sh ${RUN_ARGS} || echo "[STATUS] fail"

#---kickstart a project using connect.yaml
reconnect: wipe bootstrap
	@python deploy/connect.py ${RUN_ARGS} || echo "[STATUS] fail"

#---reset with confirmation
reset:
	@bash deploy/reset.sh ${RUN_ARGS} || echo "[STATUS] fail"

#---package a multiplexer app in a standalone folder and install
package:
	@bash deploy/package.sh ${RUN_ARGS} || echo "[STATUS] fail"

#---clear the package directory
depack:
	@bash deploy/depack.sh ${RUN_ARGS} || echo "[STATUS] fail"
	
#---delete and recreate the virtualenv
bootstrap:
	@bash deploy/bootstrap.sh || echo "[STATUS] fail"

#---reset everything with no confirmation and also obliterate data and calc
wipe:
	@bash deploy/wipe.sh || echo "[STATUS] fail"

#---reset the development environment
devclean:
	@bash deploy/devclean.sh || echo "[STATUS] fail"	

#---reset the omnicalc repo during development
omninuke:
	@bash deploy/devomni.sh || echo "[STATUS] fail"
	
connect: 
	@python deploy/connect.py ${RUN_ARGS} || echo "[STATUS] fail"

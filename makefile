
#---INTERFACE TO CONTROLLER
#-------------------------------------------------------------------------------------------------------------

#---filter and evaluate
-include banner
RUN_ARGS_UNFILTER := $(wordlist 1,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
RUN_ARGS := $(filter-out banner run shutdown shell kickstart package bootstrap \
	reset connect reconnect wipe devclean nuke help,$(RUN_ARGS_UNFILTER))
$(eval $(RUN_ARGS):;@:)

#---show the banner if no targets
banner:
	@sed -n 1,11p deploy/README.md

#---useful hints
help:
	@tail -n +12 deploy/README.md

#---do not target arguments if using python
.PHONY: banner ${RUN_ARGS}

#---start a server and detach the screen
run: shutdown
	@bash deploy/run.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---refresh connections via descriptions in a yaml file
connect: 
	@python deploy/connect.py ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---reattach the screen running the server
shutdown:
	@bash deploy/shutdown.sh  || ( echo "[STATUS] fail" &&  exit 1 )

#---activate the virtualenvironment and run the shell
shell: 
	@bash deploy/shell.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---kickstart a new project
kickstart: bootstrap
	@bash deploy/kickstart.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---package a multiplexer app in a standalone folder and install
package:
	@bash deploy/package.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---clear the package directory
depack:
	@bash deploy/depack.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )
	
#---delete and recreate the virtualenv
bootstrap:
	@bash deploy/bootstrap.sh || ( echo "[STATUS] fail" &&  exit 1 )

#---erase everything and start from scratch
nuke:
	@bash deploy/nuke.sh || ( echo "[STATUS] fail" &&  exit 1 )

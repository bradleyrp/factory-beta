
### INTERFACE TO CONTROLLER

#---filter and evaluate
-include banner
VALID_TARGETS := banner run shutdown shell kickstart package bootstrap reset connect nuke help env
RUN_ARGS_UNFILTER := $(wordlist 1,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
RUN_ARGS := $(filter-out $(VALID_TARGETS),$(RUN_ARGS_UNFILTER))
$(eval $(RUN_ARGS):;@:)

#---show the banner if no targets
banner:
	@sed -n 1,10p deploy/README.md

#---warn the user if the target is invalid
ifneq ($(filter-out $(VALID_TARGETS),$(word 1,$(RUN_ARGS_UNFILTER))),)
	$(info [ERROR] "$(word 1,$(RUN_ARGS_UNFILTER))" is not a valid make target try "make help")
	$(error [ERROR] exiting)
endif

#---useful hints
help: 
	@tail -n +11 deploy/README.md

#---do not target arguments if using python
.PHONY: banner ${RUN_ARGS}

#---start a server and detach the screen
run: shutdown
	@bash deploy/run.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )
	@/bin/echo "[STATUS] see deploy/tunnelport to view the site over ssh"

#---refresh connections via descriptions in a yaml file
connect: shutdown
	@./deploy/connect.py ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---reattach the screen running the server
shutdown:
	@bash deploy/shutdown.sh  || ( echo "[STATUS] fail" &&  exit 1 )

#---activate the virtualenvironment and run the shell
shell: 
	@bash deploy/shell.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---kickstart a new project (requires three arguments, managed by connect.py)
#kickstart: env
#	@bash deploy/kickstart.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---package a multiplexer app in a standalone folder and install
package:
	@bash deploy/package.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---clear the package directory
depack:
	@bash deploy/depack.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )
	
#---delete and recreate the virtualenv
env:
	@bash deploy/bootstrap.sh ${RUN_ARGS} || ( echo "[STATUS] fail" &&  exit 1 )

#---erase everything and start from scratch
nuke:
	@bash deploy/nuke.sh || ( echo "[STATUS] fail";  exit 1 )
	@/bin/echo "[STATUS] so lonely"
	@/bin/echo "[STATUS] \"make env [system]\" to continue"

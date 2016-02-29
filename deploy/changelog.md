# CHANGELOG

## development checklist ca 2016.2.1

1. Green has segmentation faults when running VMD to trim close water. This is likely a hardware or driver issue, but it motivates the tests done on light.
2. If a simulation fails to clone automacs it doesn't leave anything on disk so the click-through-folder-delete in the admin console fails.
3. There are multiple ways to delete a simulation depending on where you click in the admin console. Specifically, if you use a checkbox and the dropdown menu to delete the record, it doesn't use the delete function which actually removes the data from the disk. Similarly, if you have a simulation that failed to clone, then doing the click-through delete will fail because the data are not on disk. This would be a useful use-case for some kind of validation and/or error reporting back to the user.
4. Using dev on a new machine requires changing paths in dev/dev/settings.
5. When deploying to light we added some package checks for e.g. python development headers but failed to correctly determine if hdf5 was correctly installed. Instead we installed it manually, along with "redis" and gromacs.
6. Since it was taking like 800 seconds to install the virtual environment, I installed scipy via zypper.
7. Redis must be installed via "sudo zypper install redis" and then the user must run redis-server deploy/redis.conf to start the message passer. Sometimes this leaves behind a dump file of some sort.

## summarizing use cases on 2016.2.11

The design of the factory codes is such that it can be used for simulations, calculations, or both. We have tried to ensure compatibility with many different incoming data types. We have tested and developed the code with the following use cases in mind. These are ranked by priority order.

1. "NEW": This is the square zero use-case. The user has no simulations or codes. A new project allows the user to start simulations. It clones omnicalc and prepares a new repo for calculations which can be offloaded to a bare repo if desired. 
2. "SIMULATIONS": The user only has simulation data. They need a new omnicalc clone and repo in order to start writing calculations.
3. "EVERYTHING": The user has simulations, postprocessing, and possibly plots, along with codes. They just probably want to look at the fancy website.
4. "NO POST": The user has simulation data and codes. Omnicalc is cloned and pulls the codes. The user is now ready to post-process the data.
5. "DEVELOPMENT": The user wants to change the omnicalc code somehow. The factory creates a new project that draws from the simulator/calculator codes in the "dev" folder. A variation of this allows the user to add parts (post,plot,repo,sims) from preexisting projects in order to develop the codes for those projects. There is no packed codes.

## updates on 2016.2.24

RPB set up omnicalc documentation.
RPB cleaned up connect.py by removing development mode and allowing any project to use "development: true" to draw from the development codes. Also cleaned up status reports on "make conenct" and ensured that omnicalc is cloned properly, and documentation is compiled.
RPB tested the "no repo" use case with the adhesion project on dark. Have not tried to test the refresh times functionality because this project uses TRRs and has no EDRS, but that would be a useful follow-up test.
Refreshing thumbnails was stuck in a loop when there were no image files so RPB added a return statement.
When importing previous data there is still a path problem when you click on the simulations. It's currently directing to the new simulations in the dropspot but it needs to look in the previous simulations.
RPB says ignore refresh times results if there is no return from work.get_timeseq. There is no error reporting for this function but it's not a crucial one.
RPB finalized the "reproduce" use case which includes an entire pipeline. This reduces the number of use cases down to three: new, reproduce, and post. The "post" use case lies somewhere in between the new/reproduce options. Most of the folder creation and cloning options handled in deploy/connect.py are flexible and won't overwrite anything.
RPB also dropped random ignore arguments on thumbnail refresh to prevent the loop (however multiple refreshes may not work).
RPB writes a function which gets data_spots paths from the omnicalc paths.py, stores it in settings.DATA_SPOTS, and then uses that to look up simulations in either the new location (dropspot) or the old ones (data_spots).

## updates on 2016.2.25

JJ and RPB determined that delays in the specs parser were due to excessive saving. This raises the question of how often we should save, and more generally, what the function of the workspace should be. Presently the workspace holds the interpreted meta files as well as the timeseries from many simulations, which mitigates the need to parse and check them very frequently (though this still happens). There is also the minor problem of some calculations requiring a "dry" parsing of the meta file, in the cases that no calculations need to be run but a plot is being made. It would be useful to outline a small number of routes by which the meta file gets in the workspace and the codes get this data. In the meantime it would be best to save less frequently.

Need to make the following changes.

1. Figure out the save behavior of the workspace.
2. report error when there is no structures.pdb
3. "command failed but nevermind" on solvate-steep in atomistic protein example but no actual error reporting.

Changes to address these issues.

1. The solvate minimizer was failing so RPB added an assertion error if the TPR file is missing. This raised the question of how to get this information to the user?
2. The problem was originally due to a filename error in the include tip3p water command in the solvate section.
3. ...
4. RPB updates tasks.py to route error to a log file. The problem is that this log file is accessed via the workspace "watch_file" throughout the codes. The watch_file is simply appended and the entire python script doesn't just log output to it. The problem is that the factory needs to get the watch file and ask the *entire automacs script* to route errors there. To do this, it needs to infer the right log file *before the script runs*. For this reason I added a detect step to get the number. We will continue the convention of naming all step scripts by the program name and number. This means that the factory can just append to the log file. Note that I forgot to append in one of the tests and this put the error at the top of the log file but still magically routed stdout to the file *afterwards* which was really weird frankly.
5. How to report errors in that log file to the user? The AJAX doesn't catch the last thing that happens because it only refreshes if a job is running. RPB started to solve this problem by figuring out how to asynchronously send a complete message from the server to client. Then realized it would be easier to just delay for more than one AJAX refresh before deleting the job. This worked and now the assertion errors show up in the console.

Other issues.

1. Need to clean up log-server, which seems to be getting the entirety of stdout from the worker. Perhaps we should route the stdout to dev/null in the tasks.py while stderr goes to the log.
2. The job queue doesn't referesh like the console. It would be nice to have a more formal job/calculation queue that is more intuitive for handling broken jobs.

Another useful idea about meta files: forget about catalogueing them. Just use every meta file in the specs folder and have the workspace report any conflicts.

## updates on 2016.2.27

RPB fixed the problem with the collections not registering simulatons with the database upon creation. The problem was that the delayed save via commit=False was breaking it, probably because it works across applications. Not sure why this flag was necessary anyway, but it was just copied from other similar lines.
Moved on to work on the refresh_times. Ran one of the test simulations a bit longer and noticed that it took two clicks to get the new data. Tested it by moving files and found that it works fine when you hide files. After troubleshooting the timing and starting to doubt the synchronicity of the underlying code I realized that I had not closed an open subprocess so it wasn't waiting for the refresh to finish. Easy fix.
RPB changed the default location for the database to the data folder. This way a reconnect won't delete it. Tested this on the current testing project and it successfully reloaded the database which means that we can now import old projects from the database.
Started working on both omni and factory to implement the new code to handle specs files. There will be a detailed description in the comments.
Also noticed that the kickstart function had the omnicalc repo hard-coded. One problem is that we cannot send a URL in the make command in the usual way. This needs fixed still.

## updates on 2016.2.28

Working on omnicalc so that it has more elegant data locations and specs files.
Note that dataspots cannot be empty and we must return to the question we asked on Friday about how to handle the rootdir in the omnicalc workspace effectively so that we can have multiple incoming/outgoing data routes. For now we manually include the dropspot as the first data_spot in use cases that require it, namely one in which the new simulations are the ones that we wish to analyze. We will have to figure out the path cross-talk logic later on for more advanced use cases where we are analyzing both old and new data. I recommended a "cursor" functionality to Joe.
Fixed connect.py so that it uses absolute data_spots paths.
Testing on some proteins and found a major error in the slicer "gmx trjconv -b 1020 -e 1000 -dt 20" so that logic needs revisited. Removed a superfluous "+1" but that was probably there for a reason so check up on it.
Added preloaded figures and tested them to create a protein_rmsd plot.
Ported the entire kickstart.sh to connect.py because there were problems in the makefile when you send an HTTP for git to the kickstarter for cloning. Also removed kickstart from the makefile.



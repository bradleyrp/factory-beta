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
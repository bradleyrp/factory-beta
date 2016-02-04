# CHANGELOG

## development checklist ca 2016.2.1

1. Green has segmentation faults when running VMD to trim close water. This is likely a hardware or driver issue, but it motivates the tests done on light.
2. If a simulation fails to clone automacs it doesn't leave anything on disk so the click-through-folder-delete in the admin console fails.
3. There are multiple ways to delete a simulation depending on where you click in the admin console. Specifically, if you use a checkbox and the dropdown menu to delete the record, it doesn't use the delete function which actually removes the data from the disk. Similarly, if you have a simulation that failed to clone, then doing the click-through delete will fail because the data are not on disk. This would be a useful use-case for some kind of validation and/or error reporting back to the user.
4. Using dev on a new machine requires changing paths in dev/dev/settings.
5. When deploying to light we added some package checks for e.g. python development headers but failed to correctly determine if hdf5 was correctly installed. Instead we installed it manually, along with "redis" and gromacs.
6. Since it was taking like 800 seconds to install the virtual environment, I installed scipy via zypper.
7. Redis must be installed via "sudo zypper install redis" and then the user must run redis-server deploy/redis.conf to start the message passer. Sometimes this leaves behind a dump file of some sort.

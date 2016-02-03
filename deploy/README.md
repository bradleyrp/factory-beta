                          

   _|               |                       
  |     _` |   __|  __|   _ \    __|  |   | 
  __|  (   |  (     |    (   |  |     |   | 
 _|   \__,_| \___| \__| \___/  _|    \__, | 
                                     ____/  

            "one-to-many"

[NOTE] use 'make help' for details

# refresh connections to project data
make connect connect.yaml

# test updates to a package in a live project:
make shutdown && make depack && make package calculator && make package simulator && make run ptdins


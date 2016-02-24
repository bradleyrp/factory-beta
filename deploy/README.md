                          

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

# start from scratch

make nuke && make connect connect.yaml && source env/bin/activate && make -C calc/$PROJECT_NAME export_to_factory $PROJECT_NAME ../../site/$PROJECT_NAME && make run $PROJECT_NAME

make nuke && make bootstrap easy && make connect connect.dark.yaml

    ___                                    
   / __)              _                    
 _| |__ _____  ____ _| |_ ___   ____ _   _ 
(_   __|____ |/ ___|_   _) _ \ / ___) | | |
  | |  / ___ ( (___  | || |_| | |   | |_| |
  |_|  \_____|\____)  \__)___/|_|    \__  |
                                    (____/ 
             "one-to-many"

[NOTE] use 'make help' for details

# start from scratch

Set up the <connect.yaml> with the appropriate name and paths. Decide whether you want an isolated virtual environment (which can be slow) or use the system flag below to use global site packages.

make nuke && make env [system] && make connect <connect.yaml> && make run <project>

# refresh connections to project data (deletes and creates the site without changing anything else)

make connect connect.yaml

# start a local server for a project

make run <project>


#!/usr/bin/python

import time
import subprocess
import os

while True:
    # Get current minute
    current_minute = time.strftime("%M")

    # Check if it's xx:00, xx:20, or xx:40
    if current_minute in ["00", "20", "40"]:
        # Get the value of $HOME
        home = os.environ['HOME']

        # Construct the full path to the newsup script
        newsup_script = os.path.join(home, "rss/scripts/newsup-torrents")

        # Run newsup
        subprocess.run([newsup_script])

    # Sleep for 60 seconds
    time.sleep(60)

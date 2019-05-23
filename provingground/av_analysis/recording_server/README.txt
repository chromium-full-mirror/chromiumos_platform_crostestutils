These scripts setup the 'recording server' and its dependencies.

Purpose:
The purpose of the recording server is to always listen for recording requests
 from DUTs, to record and then upload the results to Google storage.

Usage:
1. Create a directory 'rec_server' and copy files there.
2. Switch to newly created directory.
3. Run 'setup.sh' to setup the dependencies for the server.
4. Then execute 'run_servlet.sh' to get the server up and running.
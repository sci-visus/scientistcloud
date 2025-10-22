# For ScientistCloud 2.0, we need to start all the services in the correct order



pushd ~/ScientistCloud2.0/scientistCloudLib/Docker
git clean; ./start.sh clean; ./start.sh up
popd

pushd ~/ScientistCloud2.0/scientistcloud/SC_Docker

git pull ; ./start.sh clean ; ./start.sh 
popd

pushd ~/VisStoreClone/visus-dataportal-private/Docker 
./sync_with_github.sh ; ./scientistCloud_docker_start_fresh.sh x; ./setup_ssl.sh 

popd

pushd ~/ScientistCloud2.0/scientistcloud/SC_Docker

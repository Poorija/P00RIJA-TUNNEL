#!/bin/bash
docker rm -f $(docker ps -a -q -f "ancestor=p00rija-tunnel:1.9.95") 2>/dev/null
docker rmi p00rija-tunnel:1.9.95 2>/dev/null
docker network rm p00rija-test-net 2>/dev/null
docker network rm rt-panel-net rt-iran-panel-net rt-iran-node-2-net rt-foreign-node-1-net rt-foreign-node-2-net rt-foreign-node-3-net 2>/dev/null
rm -rf tests/realistic-load tests/panel tests/iran-node-* tests/foreign-node-* tmp/p00rija_test_rebuild

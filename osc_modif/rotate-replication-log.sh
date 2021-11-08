#! /bin/bash

set -e

cd /data/work/osmbin

if [ -e replication.log.1 ]; then
  gzip replication.log.1
fi

for i in $(seq 30 -1 1); do
  if [ -e replication.log.$i.gz ]; then
    mv replication.log.$i.gz replication.log.$(($i+1)).gz;
  fi
done

mv replication.log replication.log.1
touch replication.log

if [ -e merge.log.1 ]; then
  gzip merge.log.1
fi

for i in $(seq 30 -1 1); do
  if [ -e merge.log.$i.gz ]; then
    mv merge.log.$i.gz merge.log.$(($i+1)).gz;
  fi
done

mv merge.log merge.log.1
touch merge.log

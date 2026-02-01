#!/bin/zsh

DATA_DIR="/usr/local/var/postgresql@18/"
# check if postgres server is running
if [ ! -f $DATA_DIR/postmaster.pid ]; then
    # start postgres server
    pg_ctl -D $DATA_DIR start -s -l "postgres_`date +%Y%m%d_%H%M%S`.log"
else
   echo "postgres server is already running..."
   IS_POSTGRES_RUNNING=true
fi

psql -d postgres -f deletedb.psql

# stop postgres server if we start it
if expr $IS_POSTGRES_RUNNING = false > /dev/null; then
    pg_ctl -D $DATA_DIR -s stop
fi
#!/bin/bash

# Scheduled database dumps to ensure you have a clean backup
# Based on https://mariadb.com/kb/en/making-backups-with-mysqldump/

# The --lock-tables flag is used and locks all tables for the duration of the mysqldump, its a bad option if the
# server is heavily used.

# You need to give in the correct OUTPUT folder below. Create the dbs folder if it doesnt exist.
# Run follwing command after creating the file
# chmod + mariadb-backup.sh

# Then, use the following command to securely setup auto login for the script (you'll be prompter for the password)
# mysql_config_editor set --login-path=/home/ubuntu --host=localhost --user=backup --password

# Check the mysql login is configured
# mysql_config_editor print --all

# Setup a cron job using the standard user, i.e. sudo crontab -e
# 32 0 * * * /home/ununtu/mysql-backup.sh

# To uncmpress the SQL dumps use the command line tool funzip <filename.sql.gz>

BACKUP_DIR="/home/ubuntu/dbs"

mysqldump --user=backup --password --lock-tables --all-databases | gzip -9 > "$BACKUP_DIR/dbs/db-$DATE.sql.gz"
find $BACKUP_DIR/* -mtime +5 -exec rm {} \;

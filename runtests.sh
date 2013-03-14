#!/bin/bash
#
# ./runtests.sh -v -w yabitests
# ./runtests.sh -v -w yabitests --collect-only
# ./runtests.sh -v -w yabitests yabitests.backend_restart_tests
#
source virt_yabiadmin/bin/activate

if [ "$YABI_CONFIG" = "" ]; then
    YABI_CONFIG="test_mysql"
fi

case $YABI_CONFIG in
test_mysql)
    export PYTHONPATH=yabiadmin
    export DJANGO_SETTINGS_MODULE="yabiadmin.testmysqlsettings"
    ;;
dev_mysql)
    export PYTHONPATH=yabiadmin
    export DJANGO_SETTINGS_MODULE="yabiadmin.settings"
    ;;
dev_postgres)
    export PYTHONPATH=yabiadmin
    export DJANGO_SETTINGS_MODULE="yabiadmin.postgresqlsettings"
    ;;
quickstart)
    export DJANGO_SETTINGS_MODULE="yabiadmin.quickstartsettings"
    ;;
*)
    echo "No YABI_CONFIG set, exiting"
    exit 1
esac

python -c "from django.db import models"
python -c "import $DJANGO_SETTINGS_MODULE"
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"

./yabictl.sh stop
./yabictl.sh start

nosetests $@

./yabictl.sh stop

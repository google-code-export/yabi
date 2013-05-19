#!/bin/bash
#
# Script to control Yabi in dev and test
#

# break on error
set -e 

ACTION="$1"
PROJECT="$2"

PORT='8000'

PROJECT_NAME='yabi'
AWS_BUILD_INSTANCE='rpmbuild-centos6-aws'
TARGET_DIR="/usr/local/src/${PROJECT_NAME}"
CLOSURE="/usr/local/closure/compiler.jar"
MODULES="MySQL-python==1.2.3 psycopg2==2.4.6 Werkzeug flake8"
PIP_OPTS="-v -M --download-cache ~/.pip/cache"


if [ "${YABI_CONFIG}" = "" ]; then
    YABI_CONFIG="dev_mysql"
fi


function usage() {
    echo ""
    echo "Usage ./develop.sh (status|test_mysql|test_postgresql|test_yabiadmin|lint|jslint|dropdb|start|stop|install|clean|purge|pipfreeze|pythonversion|ci_remote_build|ci_rpm_publish|ci_remote_destroy) (yabiadmin|yabibe|yabish)"
    echo ""
}


function project_needed() {
    if ! test ${PROJECT}; then
        usage
        exit 1
    fi
}


function settings() {
    case ${YABI_CONFIG} in
    test_mysql)
        export DJANGO_SETTINGS_MODULE="yabiadmin.testmysqlsettings"
        ;;
    test_postgresql)
        export DJANGO_SETTINGS_MODULE="yabiadmin.testpostgresqlsettings"
        ;;
    dev_mysql)
        export DJANGO_SETTINGS_MODULE="yabiadmin.settings"
        ;;
    dev_postgresql)
        export DJANGO_SETTINGS_MODULE="yabiadmin.postgresqlsettings"
        ;;
    *)
        echo "No YABI_CONFIG set, exiting"
        exit 1
    esac

    echo "Config: ${YABI_CONFIG}"
}


# ssh setup, make sure our ccg commands can run in an automated environment
function ci_ssh_agent() {
    ssh-agent > /tmp/agent.env.sh
    source /tmp/agent.env.sh
    ssh-add ~/.ssh/ccg-syd-staging.pem
}


# build RPMs on a remote host from ci environment
function ci_remote_build() {
    project_required

    time ccg ${AWS_BUILD_INSTANCE} puppet
    time ccg ${AWS_BUILD_INSTANCE} shutdown:50

    EXCLUDES="('bootstrap'\, '.hg*'\, 'virt*'\, '*.log'\, '*.rpm')"
    SSH_OPTS="-o StrictHostKeyChecking\=no"
    RSYNC_OPTS="-l"
    time ccg ${AWS_BUILD_INSTANCE} rsync_project:local_dir=./,remote_dir=${TARGET_DIR}/,ssh_opts="${SSH_OPTS}",extra_opts="${RSYNC_OPTS}",exclude="${EXCLUDES}",delete=True
    time ccg ${AWS_BUILD_INSTANCE} build_rpm:centos/${PROJECT}/${PROJECT}.spec,src=${TARGET_DIR}

    mkdir -p build
    ccg ${AWS_BUILD_INSTANCE} getfile:rpmbuild/RPMS/x86_64/${PROJECT}*.rpm,build/
}


# publish rpms 
function ci_rpm_publish() {
    project_needed
    time ccg ${AWS_BUILD_INSTANCE} publish_rpm:build/${PROJECT}*.rpm,release=6
}


# destroy our ci build server
function ci_remote_destroy() {
    ccg ${AWS_BUILD_INSTANCE} destroy
}


# lint using flake8
function lint() {
    project_needed
    virt_yabiadmin/bin/flake8 ${PROJECT} --ignore=E501 --count
}


# lint js, assumes closure compiler
function jslint() {
    JSFILES="yabiadmin/yabiadmin/yabifeapp/static/javascript/*.js yabiadmin/yabiadmin/yabifeapp/static/javascript/account/*.js"
    for JS in $JSFILES
    do
        java -jar ${CLOSURE} --js $JS --js_output_file output.js --warning_level DEFAULT --summary_detail_level 3
    done
}


function nosetests() {
    source virt_yabiadmin/bin/activate
    # Runs the end-to-end tests in the Yabitests project
    virt_yabiadmin/bin/nosetests --with-xunit --xunit-file=tests.xml -I torque_tests.py -v -w tests

    #virt_yabiadmin/bin/nosetests -v -w tests tests.simple_tool_tests
    #virt_yabiadmin/bin/nosetests -v -w tests  tests.s3_connection_tests
    #virt_yabiadmin/bin/nosetests -v -w tests  tests.ssh_tests
}


function noseyabiadmin() {
    source virt_yabiadmin/bin/activate
    # Runs the unit tests in the Yabiadmin project
    virt_yabiadmin/bin/nosetests --with-xunit --xunit-file=yabiadmin.xml -v -w yabiadmin/yabiadmin 
}


function nose_collect() {
    source virt_yabiadmin/bin/activate
    virt_yabiadmin/bin/nosetests -v -w tests --collect-only
}


function dropdb() {

    case ${YABI_CONFIG} in
    test_mysql)
        mysql -v -uroot -e "drop database test_yabi;" || true
        mysql -v -uroot -e "create database test_yabi default charset=UTF8;" || true
        ;;
    test_postgresql)
        psql -aeE -U postgres -c "SELECT pg_terminate_backend(pg_stat_activity.procpid) FROM pg_stat_activity where pg_stat_activity.datname = 'test_yabi'" && psql -aeE -U postgres -c "alter user yabminapp createdb;" template1 && psql -aeE -U postgres -c "alter database test_yabi owner to yabminapp" template1 && psql -aeE -U yabminapp -c "drop database test_yabi" template1 && psql -aeE -U yabminapp -c "create database test_yabi;" template1
        ;;
    dev_mysql)
	echo "Drop the dev database manually:"
        echo "mysql -uroot -e \"drop database dev_yabi; create database dev_yabi default charset=UTF8;\""
        exit 1
        ;;
    dev_postgresql)
	echo "Drop the dev database manually:"
        echo "psql -aeE -U postgres -c \"SELECT pg_terminate_backend(pg_stat_activity.procpid) FROM pg_stat_activity where pg_stat_activity.datname = 'dev_yabi'\" && psql -aeE -U postgres -c \"alter user yabminapp createdb;\" template1 && psql -aeE -U yabminapp -c \"drop database dev_yabi\" template1 && psql -aeE -U yabminapp -c \"create database dev_yabi;\" template1"
        exit 1
        ;;
    *)
        echo "No YABI_CONFIG set, exiting"
        exit 1
    esac
}


function stopprocess() {
    set +e
    if test -e $1; then
        kill `cat $1`
    fi
    
    for I in {1..10} 
    do
        if test -e $1; then
            sleep 1
        else
            break
        fi
    done

    if test -e $1; then
        kill -9 `cat $1`
        rm -f $1
        echo "Forced stop"
    fi
    set -e
}


function stopyabiadmin() {
    echo "Stopping Yabi admin"
    stopprocess yabiadmin-develop.pid
}


function stopceleryd() {
    echo "Stopping celeryd"
    stopprocess celeryd-develop.pid
}


function stopyabibe() {
    echo "Stopping Yabi backend"
    stopprocess yabibe-develop.pid
}


function stopyabi() {
    case ${PROJECT} in
    'yabiadmin')
        stopyabiadmin
        stopceleryd
        ;;
    'yabibe')
        stopyabibe
        ;;
    '')
        stopyabiadmin
        stopceleryd
        stopyabibe
        ;;
    *)
        echo "Cannot stop ${PROJECT}"
        usage
        exit 1
        ;;
    esac
}


function installyabi() {
    # check requirements
    which virtualenv >/dev/null

    echo "Install yabiadmin"
    virtualenv --system-site-packages virt_yabiadmin
    pushd yabiadmin
    ../virt_yabiadmin/bin/pip install ${PIP_OPTS} -e .
    popd
    virt_yabiadmin/bin/pip install ${PIP_OPTS} ${MODULES}

    echo "Install yabibe"
    virtualenv --system-site-packages virt_yabibe
    pushd yabibe
    ../virt_yabibe/bin/pip install ${PIP_OPTS} -e .
    popd

    echo "Install yabish"
    pushd yabish
    ../virt_yabibe/bin/pip install ${PIP_OPTS} -e .
    popd
}


function startyabiadmin() {
    if test -e yabiadmin-develop.pid; then
        echo "pid file exists for yabiadmin"
        return
    fi

    echo "Launch yabiadmin (frontend) http://localhost:${PORT}"
    mkdir -p ~/yabi_data_dir
    virt_yabiadmin/bin/django-admin.py syncdb --noinput --settings=${DJANGO_SETTINGS_MODULE} 1> syncdb-develop.log
    virt_yabiadmin/bin/django-admin.py migrate --settings=${DJANGO_SETTINGS_MODULE} 1> migrate-develop.log
    virt_yabiadmin/bin/django-admin.py collectstatic --noinput --settings=${DJANGO_SETTINGS_MODULE} 1> collectstatic-develop.log
    virt_yabiadmin/bin/gunicorn_django -b 0.0.0.0:${PORT} --pid=yabiadmin-develop.pid --log-file=yabiadmin-develop.log --daemon ${DJANGO_SETTINGS_MODULE} -t 300 -w 5
}


function startceleryd() {
    if test -e celeryd-develop.pid; then
        echo "pid file exists for celeryd"
        return
    fi

    echo "Launch celeryd (message queue)"
    CELERY_CONFIG_MODULE="settings"
    CELERYD_CHDIR=`pwd`
    CELERYD_OPTS="--logfile=celeryd-develop.log --pidfile=celeryd-develop.pid"
    CELERY_LOADER="django"
    DJANGO_PROJECT_DIR="$CELERYD_CHDIR"
    PROJECT_DIRECTORY="$CELERYD_CHDIR"
    export CELERY_CONFIG_MODULE DJANGO_SETTINGS_MODULE DJANGO_PROJECT_DIR CELERY_LOADER CELERY_CHDIR PROJECT_DIRECTORY CELERYD_CHDIR
    virt_yabiadmin/bin/celeryd $CELERYD_OPTS 1>/dev/null 2>/dev/null &
}


function startyabibe() {
    if test -e yabibe-develop.pid; then
        echo "pid file exists for yabibe"
        return
    fi

    echo "Launch yabibe (backend)"
    mkdir -p ~/.yabi/run/backend/certificates
    mkdir -p ~/.yabi/run/backend/fifos
    mkdir -p ~/.yabi/run/backend/tasklets
    mkdir -p ~/.yabi/run/backend/temp

    virt_yabibe/bin/yabibe --pidfile=yabibe-develop.pid
}


function startyabi() {
    case ${PROJECT} in
    'yabiadmin')
        startyabiadmin
        startceleryd
        ;;
    'yabibe')
        startyabibe
        ;;
    '')
        startyabiadmin
        startceleryd
        startyabibe
        ;;
    *)
        echo "Cannot start ${PROJECT}"
        usage
        exit 1
        ;;
    esac
}


function yabistatus() {
    set +e
    if test -e yabibe-develop.pid; then
        ps -f -p `cat yabibe-develop.pid`
    else 
        echo "No pid file for yabibe"
    fi
    if test -e yabiadmin-develop.pid; then
        ps -f -p `cat yabiadmin-develop.pid`
    else 
        echo "No pid file for yabiadmin"
    fi
    if test -e celeryd-develop.pid; then
        ps -f -p `cat celeryd-develop.pid`
    else 
        echo "No pid file for celeryd"
    fi
    set -e
}


function pythonversion() {
    virt_yabiadmin/bin/python -V
    virt_yabibe/bin/python -V
}


function pipfreeze() {
    echo 'yabiadmin pip freeze'
    virt_yabiadmin/bin/pip freeze
    echo '' 
    echo 'yabibe pip freeze' 
    virt_yabibe/bin/pip freeze
}


function yabiclean() {
    echo "rm -rf ~/.yabi/run/backend"
    rm -rf ~/.yabi/run/backend
    find yabibe -name "*.pyc" -exec rm -rf {} \;
    find yabiadmin -name "*.pyc" -exec rm -rf {} \;
    find yabish -name "*.pyc" -exec rm -rf {} \;
    find tests -name "*.pyc" -exec rm -rf {} \;
}


function yabipurge() {
    rm -rf virt_yabiadmin
    rm -rf virt_yabibe
    rm *.log
}


function dbtest() {
    stopyabi
    dropdb
    startyabi
    nosetests
    stopyabi
}


function yabiadmintest() {
    stopyabi
    dropdb
    startyabi
    noseyabiadmin
    stopyabi
}


case ${PROJECT} in
'yabiadmin' | 'yabibe' | 'yabish' | '')
    ;;
*)
    usage
    exit 1
    ;;
esac

case $ACTION in
pythonversion)
    pythonversion
    ;;
pipfreeze)
    pipfreeze
    ;;
test_mysql)
    YABI_CONFIG="test_mysql"
    settings
    dbtest
    ;;
test_postgresql)
    YABI_CONFIG="test_postgresql"
    settings
    dbtest
    ;;
test_yabiadmin_mysql)
    YABI_CONFIG="test_mysql"
    settings
    yabiadmintest
    ;;
lint)
    lint
    ;;
jslint)
    jslint
    ;;
dropdb)
    settings
    dropdb
    ;;
stop)
    settings
    stopyabi
    ;;
start)
    settings
    startyabi
    ;;
status)
    yabistatus
    ;;
install)
    settings
    stopyabi
    installyabi
    ;;
ci_remote_build)
    ci_ssh_agent
    ci_remote_build
    ;;
ci_remote_destroy)
    ci_ssh_agent
    ci_remote_destroy
    ;;
ci_rpm_publish)
    ci_ssh_agent
    ci_rpm_publish
    ;;
clean)
    settings
    stopyabi
    yabiclean 
    ;;
purge)
    settings
    stopyabi
    yabiclean
    yabipurge
    ;;
*)
    usage
    ;;
esac

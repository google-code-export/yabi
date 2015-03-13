_This page has been replaced by QuickStart which is the new way of getting Yabi running for developers_

### Dependencies ###
  * Python
  * python include headers
  * Stackless Python setup as per [BuildingStacklessPython](BuildingStacklessPython.md)
  * Memcached running on the local machine (or change the yabi settings to point at your memcached server)
  * sqlite3 (or other database supported by Django)
  * Mercurial

### Checkout source code ###

Yabi is stored in a mercurial repository. All three main components are in the same repository, so only one checkout is required.
```
hg clone https://code.google.com/p/yabi/
```

### Running Yabi ###
To run Yabi you need to start Yabi Frontend, Yabi Admin Console and the Yabi Backend.

#### Yabi Frontend ####
```
cd yabi/yabife/yabife/

# Create a virtual python environment
sh ../../bootstrap.sh -r quickstart.txt

# Activate virtual python
﻿source virt_yabife/bin/activate

# Create the database
﻿python manage.py syncdb --noinput

# Run database migrations
python manage.py migrate

# Start Yabi Frontend
gunicorn_django -w 5 -b 127.0.0.1:8000
```

#### Yabi Admin ####

In a new terminal cd into the same yabi clone directory then:

```
cd yabiadmin/yabiadmin/

# Create a virtual python environment
sh ../../bootstrap.sh -r quickstart.txt

# Activate virtual python
﻿source virt_yabiadmin/bin/activate

# Create the database
﻿python manage.py syncdb --noinput

# Run database migrations
python manage.py migrate

# Start Yabi Management console
gunicorn_django -b 127.0.0.1:8001
```


#### Celery ####

In a new terminal cd into the same yabi clone directory then:

```
cd yabiadmin/yabiadmin/
```

The virtual environment is already set up so you can run:
```
# Activate virtual python
source virt_yabiadmin/bin/activate

# start celery
fab celeryd_quickstart
```


#### Backend ####

Create essential directories in the home directory of the user running the backend.

```
mkdir -p ~/.yabi/run/backend/fifos/ ~/.yabi/run/backend/tasklets/ ~/.yabi/run/backend/temp/ ~/.yabi/run/backend/certificates/
```

Now bootstrap a virtual python based on your stackless python.

```
cd yabibe/yabibe/

# Create a virtual python environment based on your stackless install
# this assumes your stackless binary is called 'spython' as per our build recommendations
sh ../../bootstrap.sh -p /usr/local/bin/spython -r requirements.txt

# Activate virtual python
﻿source virt_yabibe/bin/activate

# start your backend
fab backend
```

### Access ###

﻿http://127.0.0.1:8000/
- username:demo password:demo

﻿http://127.0.0.1:8001/admin/
- username:admin password:admin


### Troubleshooting ###
  * If you wish to use a database other than sqlite then you will need to edit the yabife and yabiadmin settings.py files to point at the correct database.
If you want to give access to other users to be able to interact with the admin you need to add them as admistration users. There are two ways of doing this.

  1. Add them as a superuser by clicking the appropriate box on their Auth User record in the admin. This will give them all rights.

> 2. Follow your nose in Auth Groups, set up a new group with the permissions you want to allow, probably all yabmin and yabiengine actions. Then in Auth Users add the user to that newly created group.
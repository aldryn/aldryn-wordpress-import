aldryn-wordpress-import
=======================

Wordpress import for aldryn-blog.


Usage
=====
* Pick wordpress instalation and create XML file with posts (Admin→Tools→Export)
* Go to /admin on aldryn site and choose Wordpress Import from menu
* Create new wordpress import and upload xml file
* Open this import in django admin
* Click 'Perform import' button in top-right corner
* When import is done you should receive js alert 'Done'
* Page will refresh and logfile should be visible
* Import may take a while, depending on number of posts to import
* Request can be observed in Network tab in browser developer tools

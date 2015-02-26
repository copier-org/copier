========
Usage
========

To use Voodoo in a project::

	import voodoo

To install a template use install <url>. For example::

  voodoo install http://clay <name>

Optionally an extra argument can be passed to install which is the name to save the template as.

You can verify that the template was installed typing::

  voodoo list

You can then use the template with::

  voodoo new clay <destination_path>

Optionally an extra argument can be passed to install which is the path of where to render the template to. If omitted  to save the template as.

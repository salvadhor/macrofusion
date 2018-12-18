About
-------

MacroFusion is a neat little GUI for the great tool `Enfuse`
(command line). It makes it easy to fuse many photos to one with great
DOF (Depth of Field) or DR (Dynamic Range). Useful for every macro
lover or landscaper.

MacroFusion is a fork of EnfuseGui of Chez Gholyo. Rebranding is due to
conflict with another EnfuseGui (for MacOS).

This program is free software under the terms of GNU GPLv3.



Dependencies:
---------
- python (>=3)
- Pillow (fork of PIL) (python3-imaging)
- gexiv2 (gir1.2-gexiv2)
- exiftool (libimage-exiftool-perl)
- enfuse (>=4.0)
- hugin-tools (with align_image_stack)

Local install (archive .tar.gz):
------
- Unpack
- Go to the directory `macrofusion-0.X`
- Run `./macrofusion.py`

System wide install:
-------
Use PPA or .deb packages (the only packages so far).

PPA (Ubuntu Trusty, Mint 17)

sudo add-apt-repository ppa:dhor/myway

(https://launchpad.net/~dhor/+archive/myway)

Mint and Debian users also can use that .deb.


Translations
--------------

To translate MacroFusion, use macrofusion.pot (original strings)
and POEditor (or any utility you like).
Import strings from .pot file and save them as .po.
Send it to me after you've done - thanks in advance.


Questions and answers
---------------------

Q: Who needs ugly GUI for great command-line tool?  
A: Users that use Linux on a daily basis.

Q: Enfuse in text mode is very simply to use.  
A: That's right. But we are in the XXI century - time to use mouse.

Q: What a stupid idea - put photos together. Who cares.  
A: That's right, but the other platforms have tools to do that, so why don't do
that on Linux? Photographers care.

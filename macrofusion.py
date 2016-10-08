#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# License : GPLv3 : http://gplv3.fsf.org/

APP             = 'MacroFusion'
__VERSION__     ='0.7.5'
__LICENSE__     ='GPL'
__COPYRIGHT__   ='Dariusz Duma'
__WEBSITE__     ='http://sourceforge.net/p/macrofusion'

try:

    import os, sys
    import os.path
    import subprocess
    import shutil
    import time
    import threading   
    import multiprocessing
    import re
    import configparser
    import operator
    import cairo
    import random
    import urllib.parse
    import signal
    import tempfile
    import locale


    from gi import require_version
    require_version('Gtk', '3.0')
    require_version('Gdk', '3.0')
    require_version('GExiv2', '0.10')
    from gi.repository import Gdk, Gtk, GObject, GdkPixbuf, GExiv2

except:    
    print('An error occured. Python or one of its sub modules is absent...\nIt would be wise to check your python installation.')
    sys.exit(1)    

try:
    from PIL import Image
except:
    print('Python Imaging Library is missing.')


if os.path.exists('/usr/share/mfusion/ui/ui.xml') \
    and os.path.exists('/usr/share/mfusion/ui/progress.xml') \
    and os.path.exists('/usr/share/pixmaps/macrofusion.png') \
    and os.path.exists('/usr/share/mfusion/images/logoSplash.png'):
    # print ("System wide install!")
    DIR = '/usr/share/locale/'
    IMG = '/usr/share/pixmaps/'
    IMG2 = '/usr/share/mfusion/images/'
    UI = '/usr/share/mfusion/ui/'
elif os.path.exists(sys.path[0] + "/ui/ui.xml"):
    # print ("Local run!")
    DIR = sys.path[0] + '/locale/'
    IMG = sys.path[0] + '/images/'
    IMG2 = sys.path[0] + '/images/'
    UI = sys.path[0] + '/ui/'
else:
    print ("That's me, your MacroFusion. Make your mind - local or system wide install?")
    sys.exit(1)


from locale import gettext as _
locale.bindtextdomain(APP, DIR)
locale.textdomain(APP)


GObject.threads_init()

def toggled_cb(cell, path, user_data):
    model, column = user_data
    model[path][column] = not model[path][column]
    return

# PLEASE REAPAIR!! Python-imaging can't open .tiff (or some of them)    
def create_thumbnail(chemin,taille):
    outfile = settings["preview_folder"] + '/' + os.path.split(chemin)[1]
    try:
        im = GdkPixbuf.Pixbuf.new_from_file_at_size(chemin, taille[0], taille[1])
#        pb = Gtk.gdk.pixbuf_new_from_file(chemin)
#        im = Interface.pixbuf2Image(Interface(),pb)
#        im = Image.open(chemin)
#        im.thumbnail(taille)
#        im.save(outfile, "JPEG")
        im.savev(outfile, "jpeg", [], [])
    except IOError:
        print(_("Generating %s thumbnail failed.") % chemin)
    return outfile


####################################################
########Classe des données##########################
####################################################
enfuse_gray_projector_options = ["anti-value", "average", "l-star", "lightness", "value", "luminance", "pl-star"]
tiff_compression = {0:"NONE", 1:"PACKBITS", 2:"LZW", 3:"DEFLATE"}
settings = {
    "install_folder"            : sys.path[0],
    "config_folder"             : os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config/mfusion'),
    "default_folder"            : os.path.expanduser('~/'),
    "temp_folder"               : tempfile.gettempdir(),
    "align_prefix"              : "aligned",
    "default_file"              : "",
    "files"                     : [ ],
    "enfuser"                   : "enfuse",
    "cpus"                      : 1,
    "align_settings"            :
    {
        # Auto crop the image to the area covered by all images.
        "auto_crop"             : ["-C",        True],
        # Optimize image center shift for all images, except for first.
        "opt_img_shift"         : ["-i",        True],
        # Optimize field of view for all images, except for first.
        # Useful for aligning focus stacks with slightly different magnification.
        "opt_fov"               : ["-m",        True],
        # Use GPU for remapping.
        "use_gpu"               : ["--gpu",     True],
        # Correlation threshold for identifying control points (default: 0.9).
        "corr_thres"            : ["--corr",    0.6],
        # Number of control points (per grid, see option -g) to create between adjacent images (default: 8).  
        "num_ctrl_pnt"          : ["-c",        20],
        # Scale down image by 2^scale (default: 1). Scaling down images will improve speed at the cost of accuracy.
        "scale_down"            : ["-s",        0],
        # Misc arguments
        "misc_args"             : ["",          False]
    },
    "fuse_settings"             :
    {
        # default compression setting (for JPG/TIFF) 
        "compression"           : ["--compression",             "100"],
        # weight given to well-exposed pixels
        "exposure-weight"       : ["--exposure-weight",         1.0],
        # weight given to highly-saturated pixels
        "saturation-weight"     : ["--saturation-weight",       0.2],
        # weight given to pixels in high-contrast neighborhoods
        "contrast-weight"       : ["--contrast-weight",         0.0],
        # mean of Gaussian weighting function
        "exposure-mu"           : ["--exposure-mu",             0.5],
        # standard deviation of Gaussian weighting function 
        "exposure-sigma"        : ["--exposure-sigma",          0.2],
        # limit number of blending LEVELS to use (1 to 29)
        "levels"                : ["--levels",                  29],
        # average over all masks; this is the default
        "soft-mask"             : ["--soft-mask",               True],
        # force hard blend masks and no averaging on finest scale
        "hard-mask"             : ["--hard-mask",               False],
        # apply gray-scale PROJECTOR in exposure or contrast weighing, where PROJECTOR is one of
        # 0: "anti-value", 1: "average", 2: "l-star", 3: "lightness", 4: "luminance", 5: "pl-star", 6: "value"
        "gray-projector"        : ["--gray-projector",          1],
        # set window SIZE for local-contrast analysis     
        "contrast-window-size"  : ["--contrast-window-size",    3],
        # minimum CURVATURE for an edge to qualify; append "%" for relative values
        "contrast-min-curvature": ["--contrast-min-curvature",  0],
        # set scale on which to look for edges; positive LCESCALE switches on.
        # local contrast enhancement by LCEFACTOR (EDGESCALE, LCESCALE, LCEFACTOR >= 0);
        # append "%" to LCESCALE for values relative to EDGESCALE; append "%" to LCEFACTOR for relative value
        "contrast-edge-scale"   : ["--contrast-edge-scale",     0, 0, 0],
        # use CIECAM02 to blend colors
        "use_ciecam"            : ["-c",                        False],
        # save masks to files
        #"save-masks"            : ["--save-masks", "%f-softmask-%n.png:%f-hardmask-%n.png"],
        # load masks from files
        #"load-masks"            : ["--load-masks", "%f-softmask-%n.png:%f-hardmask-%n.png"],
        # image CACHESIZE in megabytes; default: 1024MB
        "image_cachesize"       : ["-m",                        4096],
        # image cache BLOCKSIZE in kilobytes; default: 2048KB
        "image_cacheblocksize"  : ["-b",                        4096],
        # Misc arguments
        "misc_args"             : ["",                          False]
    }
}

class data:
    """Données utiles"""
    def __init__(self):
        self.update_folders()
        settings["cpus"] = multiprocessing.cpu_count()
        if settings["cpus"] > 1 and self.check_install("enfuse-mp"):
            print("Will use all the powers of your CPU!")
            settings["enfuser"] = "enfuse-mp"
        else:  
            settings["enfuser"] = "enfuse"

    def update_folders(self):        
        # save tmp files in current working folder
        settings["enfuse_folder"]  = settings["temp_folder"]
        settings["preview_folder"] = settings["temp_folder"] + "/preview"
        
        if not os.path.exists(settings["config_folder"]):
            os.makedirs(settings["config_folder"])
        if not os.path.exists(settings["enfuse_folder"]):
            os.makedirs(settings["enfuse_folder"])
        if not os.path.exists(settings["preview_folder"]):
            os.makedirs(settings["preview_folder"])

    def get_enfuse_options(self):
        options = []
        for key, value in settings["fuse_settings"].items():
            # special treatment for boolean values
            if (key == "soft-mask" or key == "hard-mask" or key == "use_ciecam" or key == "misc_args"):
                if value[1]:
                    options.append(value[0])
            elif key == "gray-projector":
                options.append(value[0] + "=" + enfuse_gray_projector_options[value[1]])
            elif key == "contrast-edge-scale" and value[1]:
                options.append(value[0] + "=" + str(value[1]) + ":" + str(value[2]) + ":" + str(value[3]))
            else:
                if value[1]:
                    if "--" in value[0]:
                        options.append(value[0] + "=" + str(value[1]))
                    else:
                        options.append(value[0] + " " + str(value[1]))
        return options

    def get_align_options(self):
        options = []
        for key, value in settings["align_settings"].items():
            # special treatment for boolean values
            if (key == "auto_crop" or key == "opt_img_shift" or key == "opt_fov" or key == "use_gpu" or key == "misc_args"):
                if value[1]:
                    options.append(value[0])
            else:
                if value[1]:
                    if "--" in value[0]:
                        options.append(value[0] + "=" + str(value[1]))
                    else:
                        options.append(value[0] + " " + str(value[1]))
        return options

    def check_install(self, name):
        a = False
        for dir in os.environ['PATH'].split(":"):
            prog = os.path.join(dir, name)
            if os.path.exists(prog): 
                a = True
        return a



##############################################################
###########Classe de l'interface##############################
##############################################################

class Interface:
    """Interface pour le logiciel d'exposition-fusion enfuse"""

    def __init__(self):
        
        # Set default icon
        Gtk.Window.set_default_icon_from_file(IMG + 'macrofusion.png') 
        
        if not data.check_install("enfuse"):
            self.messageinthebottle(_("Can't find Enfuse.\nPlease check enblend/enfuse is installed.\nStopping..."))
            sys.exit()
		        
	    #Set the Glade file
        self.gui = Gtk.Builder()
        self.gui.set_translation_domain(APP)
        self.gui.add_from_file(UI + "ui.xml")

        
        #Dans la foulee on chope la fenetre principale, ca sert a rien c'est pour
        #montrer qu'on peut le faire c'est tout ^^
        self.win=self.gui.get_object("mainwindow")
        self.win.set_title('MacroFusion' + __VERSION__)
                
        #On chope le reste, et ca, ca va servir...
        self.listeimages = self.gui.get_object("listeimages")
        self.buttonaddfile = self.gui.get_object("buttonaddfile")
        self.buttondelfile = self.gui.get_object("buttondelfile")
        self.statusbar = self.gui.get_object("status1")
        self.statusbar.push(1,(_("CPU Cores: %s") % settings["cpus"]))

        self.hscaleexp = self.gui.get_object("hscaleexp")
        self.ajus_exp = Gtk.Adjustment(value=1, lower=0, upper=1, step_incr=0.1, page_incr=0.1, page_size=0)
        self.hscaleexp.set_adjustment(self.ajus_exp)
        self.spinbuttonexp = self.gui.get_object("spinbuttonexp")
        self.spinbuttonexp.set_digits(1)
        self.spinbuttonexp.set_value(settings["fuse_settings"]["exposure-weight"][1])
        self.spinbuttonexp.set_adjustment(self.ajus_exp)
        
        self.hscalecont = self.gui.get_object("hscalecont")
        self.ajus_cont = Gtk.Adjustment(value=0, lower=0, upper=1, step_incr=0.1, page_incr=0.1, page_size=0)
        self.hscalecont.set_adjustment(self.ajus_cont)
        self.spinbuttoncont = self.gui.get_object("spinbuttoncont")
        self.spinbuttoncont.set_digits(1)
        self.spinbuttoncont.set_value(settings["fuse_settings"]["contrast-weight"][1])
        self.spinbuttoncont.set_adjustment(self.ajus_cont)
        
        self.hscalesat = self.gui.get_object("hscalesat")
        self.ajus_sat = Gtk.Adjustment(value=0.2, lower=0, upper=1, step_incr=0.1, page_incr=0.1, page_size=0)
        self.hscalesat.set_adjustment(self.ajus_sat)
        self.spinbuttonsat = self.gui.get_object("spinbuttonsat")
        self.spinbuttonsat.set_digits(1)
        self.spinbuttonsat.set_value(settings["fuse_settings"]["saturation-weight"][1])
        self.spinbuttonsat.set_adjustment(self.ajus_sat)
        
        self.hscalemu = self.gui.get_object("hscalemu")
        self.ajus_mu = Gtk.Adjustment(value=0.5, lower=0, upper=1, step_incr=0.01, page_incr=0.1, page_size=0)
        self.hscalemu.set_adjustment(self.ajus_mu)
        self.spinbuttonmu = self.gui.get_object("spinbuttonmu")
        self.spinbuttonmu.set_digits(2)
        self.spinbuttonmu.set_value(settings["fuse_settings"]["exposure-mu"][1])
        self.spinbuttonmu.set_adjustment(self.ajus_mu)
        
        self.hscalesigma = self.gui.get_object("hscalesigma")
        self.ajus_sigma = Gtk.Adjustment(value=0.2, lower=0, upper=1, step_incr=0.01, page_incr=0.1, page_size=0)
        self.hscalesigma.set_adjustment(self.ajus_sigma)
        self.spinbuttonsigma = self.gui.get_object("spinbuttonsigma")
        self.spinbuttonsigma.set_digits(2)
        self.spinbuttonsigma.set_value(settings["fuse_settings"]["exposure-sigma"][1])
        self.spinbuttonsigma.set_adjustment(self.ajus_sigma)

        self.spinbuttonlargeurprev = self.gui.get_object("spinbuttonlargeurprev")
        self.ajus_largeup = Gtk.Adjustment(value=640, lower=128, upper=1280, step_incr=1, page_incr=1, page_size=0)
        self.spinbuttonlargeurprev.set_adjustment(self.ajus_largeup)

        self.spinbuttonhauteurprev = self.gui.get_object("spinbuttonhauteurprev")
        self.ajus_hauteup = Gtk.Adjustment(value=640, lower=128, upper=1280, step_incr=1, page_incr=1, page_size=0)
        self.spinbuttonhauteurprev.set_adjustment(self.ajus_hauteup)
        
        self.buttonpreview = self.gui.get_object("buttonpreview")
        self.checkbuttontiff = self.gui.get_object("checkbuttontiff")
        self.checkbuttonjpeg = self.gui.get_object("checkbuttonjpeg")
        self.buttonfusion = self.gui.get_object("buttonfusion")   
        self.buttonbeforeafter = self.gui.get_object("buttonbeforeafter")   
        self.buttonedit = self.gui.get_object("buttoneditw")
        
        self.imagepreview = self.gui.get_object("imagepreview")
        self.imagepreview.set_from_file(IMG2 + "logoSplash.png")
        
        self.progressbar = self.gui.get_object("progressbar")
        
        self.checkbuttonexif = self.gui.get_object("checkbuttonexif")
        self.checkbuttonalignfiles = self.gui.get_object("checkbuttonalignfiles")

        #valeurs des options et configurations :
        self.check_pyramidelevel = self.gui.get_object("check_pyramidelevel")
        self.check_pyramidelevel.set_active(1)

        self.spinbuttonlevel = self.gui.get_object("spinbuttonlevel")
        self.spinbuttonlevel.set_value(settings["fuse_settings"]["levels"][1])

        self.check_hardmask = self.gui.get_object("check_hardmask")
        self.check_hardmask.set_active(settings["fuse_settings"]["hard-mask"][1])

        self.check_contwin = self.gui.get_object("check_contwin")
        self.spinbuttoncontwin = self.gui.get_object("spinbuttoncontwin")
        self.spinbuttoncontwin.set_value(settings["fuse_settings"]["contrast-window-size"][1])

        self.check_courb = self.gui.get_object("check_courb")
        self.check_prctcourb = self.gui.get_object("check_prctcourb")
        self.spinbuttoncourb = self.gui.get_object("spinbuttoncourb")
        self.spinbuttoncourb.set_value(settings["fuse_settings"]["contrast-min-curvature"][1])

        self.check_detecbord = self.gui.get_object("check_detecbord")
        self.spinbuttonEdge = self.gui.get_object("spinbuttonEdge")
        self.spinbuttonEdge.set_value(settings["fuse_settings"]["contrast-edge-scale"][1])

        self.spinbuttonLceS = self.gui.get_object("spinbuttonLceS")
        self.spinbuttonLceS.set_value(settings["fuse_settings"]["contrast-edge-scale"][2])

        self.spinbuttonLceF = self.gui.get_object("spinbuttonLceF")
        self.spinbuttonLceF.set_value(settings["fuse_settings"]["contrast-edge-scale"][3])

        self.check_lces = self.gui.get_object("check_lces")
        self.check_lcef = self.gui.get_object("check_lcef")
        
        self.check_ciecam = self.gui.get_object("check_ciecam")
        self.check_ciecam.set_active(settings["fuse_settings"]["use_ciecam"][1])

        self.check_desatmeth = self.gui.get_object("check_desatmeth")
        self.combobox_desatmet = self.gui.get_object("combobox_desatmet")
        self.combobox_desatmet.set_active(settings["fuse_settings"]["gray-projector"][1])
 
        self.spinbuttonlargeurprev = self.gui.get_object("spinbuttonlargeurprev")
        self.spinbuttonhauteurprev = self.gui.get_object("spinbuttonhauteurprev")
        self.checkbuttoncache = self.gui.get_object("checkbuttoncache")
        self.spinbuttoncache = self.gui.get_object("spinbuttoncache")
        self.checkbuttonbloc = self.gui.get_object("checkbuttonbloc")
        self.spinbuttonbloc = self.gui.get_object("spinbuttonbloc")
        self.checkbuttontaillefinale = self.gui.get_object("checkbuttontaillefinale")
        self.spinbuttonlargeurfinale = self.gui.get_object("spinbuttonlargeurfinale")
        self.spinbuttonhauteurfinale = self.gui.get_object("spinbuttonhauteurfinale")
        self.spinbuttonxoff = self.gui.get_object("spinbuttonxoff")
        self.spinbuttonyoff = self.gui.get_object("spinbuttonyoff")
        self.checkbuttonjpegorig = self.gui.get_object("checkbuttonjpegorig")
        self.hscalecomprjpeg = self.gui.get_object("hscalecomprjpeg")
        self.combtiff = self.gui.get_object("combtiff")

        self.checkbutton_a5_align = self.gui.get_object("checkbutton_a5_align")
        self.checkbutton_a5_crop = self.gui.get_object("checkbutton_a5_crop")
        self.checkbutton_a5_shift = self.gui.get_object("checkbutton_a5_shift")
        self.checkbutton_a5_field = self.gui.get_object("checkbutton_a5_field")                
        self.buttonabout = self.gui.get_object("buttonabout")
        
        self.entryedit_field = self.gui.get_object("entry_editor")                
        
        self.combobox_desatmet.set_active(0)
        self.combtiff.set_active(0)
        
        if not data.check_install('exiftool'):
            self.checkbuttonexif.set_sensitive(False)
            self.messageinthebottle(_("Exiftool is missing!\n\n Cannot copy exif info."))
        if not data.check_install('align_image_stack'):
            self.checkbutton_a5_align.set_sensitive(False)
            self.messageinthebottle(_("Hugin tools (align_image_stack) are missing !\n\n Cannot auto align images."))            

        self.checkbutton_a5_crop.set_sensitive(False)
        self.checkbutton_a5_field.set_sensitive(False)
        self.checkbutton_a5_shift.set_sensitive(False)
        self.checkbuttonalignfiles.set_sensitive(False)

        # update gui according to settings
        self.checkbutton_a5_crop.set_active(settings["align_settings"]["auto_crop"][1])
        self.checkbutton_a5_field.set_active(settings["align_settings"]["opt_fov"][1])
        self.checkbutton_a5_shift.set_active(settings["align_settings"]["opt_img_shift"][1])

        # Read values from config
        self.conf = configparser.ConfigParser()
        if os.path.isfile(settings["config_folder"] + '/mfusion.cfg'):
            self.conf.read(settings["config_folder"] + '/mfusion.cfg')
        if self.conf.has_option('prefs', 'pwidth'):
            self.spinbuttonlargeurprev.set_value(self.conf.getint('prefs', 'pwidth'))
        if self.conf.has_option('prefs', 'pheight'):
            self.spinbuttonhauteurprev.set_value(self.conf.getint('prefs', 'pheight'))
        if self.conf.has_option('prefs', 'cachebutton'):
            self.checkbuttoncache.set_active(self.conf.getboolean('prefs', 'cachebutton'))
        if self.conf.has_option('prefs', 'cachesize'):
            self.spinbuttoncache.set_value(self.conf.getint('prefs', 'cachesize'))
        if self.conf.has_option('prefs', 'blocbutton'):
            self.checkbuttonbloc.set_active(self.conf.getboolean('prefs', 'blocbutton'))
        if self.conf.has_option('prefs', 'blocsize'):
            self.spinbuttonbloc.set_value(self.conf.getint('prefs', 'blocsize'))
        if self.conf.has_option('prefs', 'outsize'):
            self.checkbuttontaillefinale.set_active(self.conf.getboolean('prefs', 'outsize'))
        if self.conf.has_option('prefs', 'outwidth'):
            self.spinbuttonlargeurfinale.set_value(self.conf.getint('prefs', 'outwidth'))
        if self.conf.has_option('prefs', 'outheight'):  
            self.spinbuttonhauteurfinale.set_value(self.conf.getint('prefs', 'outheight'))
        if self.conf.has_option('prefs', 'xoff'):
            self.spinbuttonxoff.set_value(self.conf.getint('prefs', 'xoff'))
        if self.conf.has_option('prefs', 'yoff'):  
            self.spinbuttonyoff.set_value(self.conf.getint('prefs', 'yoff'))
        if self.conf.has_option('prefs', 'jpegdef'):  
            self.checkbuttonjpegorig.set_active(self.conf.getboolean('prefs', 'jpegdef'))
        if self.conf.has_option('prefs', 'jpegcompr'):  
            self.hscalecomprjpeg.set_value(self.conf.getfloat('prefs', 'jpegcompr'))
        if self.conf.has_option('prefs', 'tiffcomp'):  
            self.combtiff.set_active(self.conf.getint('prefs', 'tiffcomp'))
        if self.conf.has_option('prefs', 'exif'):  
            self.checkbuttonexif.set_active(self.conf.getboolean('prefs', 'exif'))
        if self.conf.has_option('prefs', 'alignfiles'):
            self.checkbuttonalignfiles.set_active(self.conf.getboolean('prefs', 'alignfiles'))
        if self.conf.has_option('prefs', 'default_folder'):  
            settings["default_folder"] = self.conf.get('prefs', 'default_folder')
            if not os.path.isdir(settings["default_folder"]):
                print(_("Default folder '%s' doesn't exist, using '%s'") % (settings["default_folder"], settings["config_folder"]))
                settings["default_folder"] = os.path.expanduser('~/')
            data.update_folders()
        if self.conf.has_option('prefs', 'editor'):           
            self.entryedit_field.set_text(self.conf.get('prefs', 'editor'))
        else:
            self.entryedit_field.set_text("gimp")

        #On relie les signaux (cliques sur boutons, cochage des cases, ...) aux fonctions appropriées
        dic = { "on_mainwindow_destroy"             : self.exit_app,
                "on_buttoncancel_clicked"           : self.exit_app,
                "on_menufilequit_activate"          : self.exit_app,
                "on_menufileopen_activate"          : self.add,
                "on_buttonaddfile_clicked"          : self.add,
                "on_menufileadd_activate"           : self.add,
                "on_buttondelfile_clicked"          : self.delete,
                "on_menufiledelete_activate"        : self.delete,
                "on_buttonclear_clicked"            : self.clear,
                "on_menufileclear_activate"         : self.clear,
                "on_buttonpreview_clicked"          : self.preview,
                "on_menufilesave_activate"          : self.fusion,
                "on_buttonfusion_clicked"           : self.fusion,
                "on_buttoneditw_clicked"            : self.sendto,
                "on_buttonbeforeafter_pressed"      : self.baswitch,
                "on_buttonbeforeafter_released"     : self.baswitch,
                "on_entry_editor_activate"          : self.check_editor,
                "on_hscaleexp_format_value"         : self.apropos,
                "on_buttonabout_clicked"            : self.apropos,
                "on_checkbutton_a5_align_toggled"   : self.activate_align_options
        }
        #Auto-connection des signaux       
        self.gui.connect_signals(dic)
        
        #initialisation de la liste d'images a fusionner
        self.inittreeview()


    def activate_align_options(self, action):
        if self.checkbutton_a5_align.get_active():
            self.checkbutton_a5_crop.set_sensitive(True)
            self.checkbutton_a5_field.set_sensitive(True)
            self.checkbutton_a5_shift.set_sensitive(True)
            self.checkbuttonalignfiles.set_sensitive(True)
        else:
            self.checkbutton_a5_crop.set_sensitive(False)
            self.checkbutton_a5_field.set_sensitive(False)
            self.checkbutton_a5_shift.set_sensitive(False)
            self.checkbuttonalignfiles.set_sensitive(False)

    def exit_app(self, action):
        # cancel = self.autosave_image()
        # if cancel:
        #    return True
        self.stop_now = True
        self.closing_app = True
        self.save_settings()
        self.cleanup()
        sys.exit(0)        
    
    def check_editor(self, action):
        if not data.check_install(self.entryedit_field.get_text()):
            Gui.messageinthebottle(_("No such application!\n\n Cannot find ") + self.entryedit_field.get_text() + (_(".\n\n Revert to default value.")))
            self.entryedit_field.set_text("gimp")
            return False
        return True
        
    def cleanup(self):
        for self.files in os.walk(settings["preview_folder"]):
            for self.filename in self.files[2]:
                os.remove(settings["preview_folder"] + "/" + self.filename)
        
    def inittreeview(self):
        """initialisation de la liste d'images a importer"""
        self.liststoreimport = Gtk.ListStore(bool, str, GdkPixbuf.Pixbuf, str)                    #création de la listestore qui contiendra les noms d'images
        self.listeimages.set_model(self.liststoreimport)                        #on donne la liststore au l'afficheur treeview
        self.listeimages.set_property('tooltip-column', 3)
        
        self.colonneselect = Gtk.TreeViewColumn('')                             #Premiere colonne :
        self.listeimages.append_column(self.colonneselect)                      #on l'ajoute au TreeView
        self.select=Gtk.CellRendererToggle()                                    #On creer le cellrender pour avoir des boutons toggle
        self.colonneselect.pack_start(self.select, True)                        #on met le cellrender dans la colonne
        self.colonneselect.add_attribute(self.select, 'active', 0)              #on met les boutons actifs par défaut
        
        # self.colonneimages = Gtk.TreeViewColumn(_('Image'))                        #deuxieme colonne, titre 'Image'
        # self.listeimages.append_column(self.colonneimages)                      #on rajoute la colonne dans le treeview
        # self.cell = Gtk.CellRendererText()                                      #Ce sera des cellules de texte
        # self.colonneimages.pack_start(self.cell, True)                          #que l'on met dans la colonne
        # self.colonneimages.add_attribute(self.cell, 'text', 1)                  #et on specifie que c'est du texte simple
       
        self.colonneimages2 = Gtk.TreeViewColumn(_("Thumbnail"))                        #deuxieme colonne, titre 'Image'
        self.listeimages.append_column(self.colonneimages2)                      #on rajoute la colonne dans le treeview
        self.cell2 = Gtk.CellRendererPixbuf()                                      #Ce sera des cellules de texte
        self.colonneimages2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.colonneimages2.pack_start(self.cell2, True)                          #que l'on met dans la colonne
        self.colonneimages2.add_attribute(self.cell2, 'pixbuf', 2)
        self.cell2.set_property('visible', 1)
        
        self.listeimages.set_rules_hint(True)
        self.select.connect("toggled", toggled_cb, (self.liststoreimport, 0))   #Pour que les boutons de selection marchent

        # enable drag and drop destination for files
        self.listeimages.enable_model_drag_dest([ ('STRING', 0, 0) ], Gdk.DragAction.DEFAULT)
        self.listeimages.connect("drag_data_received", self.drag_data_received)

    def drag_data_received(self, treeview, context, x, y, selection, info, etime):
        files = selection.get_text().split()
        # remove 'file:' part and unnecessary slashes or backslashes in path
        files = [os.path.normpath(x.lstrip("file:")) for x in files]
        # get rid of 'file:' and replace %xx escapes
        files = [urllib.parse.unquote(x) for x in files]
        (path, file) = os.path.split(files[0])
        (filename, ext) = os.path.splitext(file)
        settings["default_file"] = filename+"-fused"+ext
        self.put_files_to_the_list(files)
        
    def add(self, widget):
        FenOuv=OpenFiles_Dialog(self.liststoreimport, self.win)
        self.liststoreimport=FenOuv.get_model()

    def delete(self, widget):
        self.treeselectionsuppr=self.listeimages.get_selection()                #pour récupérer quels files sont selectionnés
        self.treeselectionsuppr.set_mode(Gtk.SelectionMode.MULTIPLE)            #Pour pouvoir en selectionner plusieurs
        (model, pathlist) = self.treeselectionsuppr.get_selected_rows()
        for i in pathlist:
            treeiter = model.get_iter(i)
            self.liststoreimport.remove(treeiter) 
            
    def clear(self, widget):
        self.liststoreimport.clear()
            
    def preview(self, widget):
        self.taille=(self.spinbuttonlargeurprev.get_value(), self.spinbuttonhauteurprev.get_value())
        self.name=settings["preview_folder"] + "/" + "preview.tif"
        item=0
        if len(self.liststoreimport)>0:
            self.ref=list(zip(*self.liststoreimport))[0] 
            for item2 in self.ref:
                if item2:
                    item+=1
                    if item>1:
                        self.update_align_options()
                        self.update_enfuse_options()
                        self.thread_preview = Thread_Preview(self.taille, self.liststoreimport) 
                        self.thread_preview.start()
                        timer = GObject.timeout_add (100, self.pulsate)
                        break
        if item<=1:
            self.messageinthebottle(_("Please add or activate at least two images.\n\n Cannot do anything smart with one or no image."))


    def update_align_options(self):
        if self.checkbutton_a5_align.get_active():
            settings["align_settings"]["auto_crop"][1]     = self.checkbutton_a5_crop.get_active()
            settings["align_settings"]["opt_img_shift"][1] = self.checkbutton_a5_shift.get_active()
            settings["align_settings"]["opt_fov"][1]       = self.checkbutton_a5_field.get_active()

    def update_enfuse_options(self):
        settings["fuse_settings"]["exposure-weight"][1]     = self.spinbuttonexp.get_value()
        settings["fuse_settings"]["exposure-mu"][1]         = self.spinbuttonmu.get_value()
        settings["fuse_settings"]["exposure-sigma"][1]      = self.spinbuttonsigma.get_value()
        settings["fuse_settings"]["contrast-weight"][1]     = self.spinbuttoncont.get_value()
        settings["fuse_settings"]["saturation-weight"][1]   = self.spinbuttonsat.get_value()
        settings["fuse_settings"]["levels"][1]              = self.spinbuttonlevel.get_value_as_int()
        settings["fuse_settings"]["hard-mask"][1]           = self.check_hardmask.get_active()

        if self.check_contwin.get_active():
            settings["fuse_settings"]["contrast-window-size"][1] = self.spinbuttoncontwin.get_value_as_int()
 
        if self.check_courb.get_active():
            if self.check_prctcourb.get_active():
                settings["fuse_settings"]["contrast-min-curvature"][1] = str(self.spinbuttoncourb.get_value()) + "%"
            else:
                settings["fuse_settings"]["contrast-min-curvature"][1] = str(self.spinbuttoncourb.get_value())

        if self.check_detecbord.get_active():
            settings["fuse_settings"]["contrast-edge-scale"][1] = str(self.spinbuttonEdge.get_value())
            if self.check_lces.get_active():
                settings["fuse_settings"]["contrast-edge-scale"][2] = str(self.spinbuttonLceS.get_value()) + '%'
            else:
                settings["fuse_settings"]["contrast-edge-scale"][2] = str(self.spinbuttonLceS.get_value())
            if self.check_lcef.get_active():
                settings["fuse_settings"]["contrast-edge-scale"][3] = str(self.spinbuttonLceF.get_value()) + '%'
            else:
                settings["fuse_settings"]["contrast-edge-scale"][3] = str(self.spinbuttonLceF.get_value())
        
        if self.check_ciecam.get_active():
            settings["fuse_settings"]["use_ciecam"][1] = True

        if self.check_desatmeth.get_active():
            settings["fuse_settings"]["gray-projector"][1] = self.combobox_desatmet.get_active()

        if not self.checkbuttoncache.get_active():
            settings["fuse_settings"]["image_cachesize"][1] = self.spinbuttoncache.get_value_as_int()

        if not self.checkbuttonbloc.get_active():
            settings["fuse_settings"]["image_cacheblocksize"][1] = self.spinbuttonbloc.get_value_as_int()

        if not self.checkbuttontaillefinale.get_active():
            settings["fuse_settings"]["output_dimensions"] = [ "-f",
                                                    str(self.spinbuttonlargeurfinale.get_value_as_int()) + 'x'
                                                    + str(self.spinbuttonhauteurfinale.get_value_as_int()) + 'x'
                                                    + str(self.spinbuttonxoff.get_value_as_int()) + 'x'
                                                    + str(self.spinbuttonyoff.get_value_as_int())  ]

        if self.name.endswith(('.tif', '.tiff', '.TIF', '.TIFF')):
            settings["fuse_settings"]["compression"][1] = tiff_compression[self.combtiff.get_active()]
        if self.name.endswith(('.jpg', '.jpeg', '.JPG', '.JPEG')) and (not self.checkbuttonjpegorig.get_active()):
            settings["fuse_settings"]["compression"][1] = str(int(self.hscalecomprjpeg.get_value()))      

        
    def pulsate(self):
        if self.thread_preview.isAlive():           #Tant que le thread est en cours, 
            self.progressbar.set_text(_("Calculating preview..."))
            self.progressbar.pulse()               #on fait pulser la barre
            return True                            #et on renvoie True pour que gobject.timeout recommence
        else:
            self.progressbar.set_fraction(1)
            self.progressbar.set_text(_("Preview generated"))
            self.imagepreview.set_from_file(settings["preview_folder"] + "/" + "preview.tif")
            return False

    def baswitch(self, widget):
        if (not int(self.buttonbeforeafter.get_relief())) and (os.path.exists(settings["preview_folder"] + "/preview_.tif")):
            self.buttonbeforeafter.props.relief = Gtk.ReliefStyle.NONE
            self.imagepreview.set_from_file(settings["preview_folder"] + "/preview_.tif")
        elif os.path.exists(settings["preview_folder"] + "/preview_.tif"):
            self.buttonbeforeafter.props.relief = Gtk.ReliefStyle.NORMAL
            self.imagepreview.set_from_file(settings["preview_folder"] + "/preview.tif")
        
    def fusion(self,widget):
        if len(self.liststoreimport) <= 1:
            self.messageinthebottle(_("Please add or activate at least two images.\n\n Cannot do anything smart with the one or no image."))
            return
        FenPar = SaveFiles_Dialog(self.win)
        self.name = FenPar.get_name()
        if self.name:
            if not re.search('\\.jpeg$|\\.jpg$|\\.tiff$|\\.tif$', self.name, flags=re.IGNORECASE):
                self.name += ".jpg"
            self.start('')
    
    def sendto(self, widget):
        self.name = (settings["preview_folder"] + "/sendto.tif")
        if not os.path.exists(self.name):
            self.messageinthebottle(_("Please add or activate at least two images.\n\n Cannot do anything smart with one or no image."))
            return
        if not self.check_editor(0):
            return
        if self.start(self.name) == -1:
            self.messageinthebottle(_("No preview, no output, no edit.\n\n Game Over."))
            return
        
    def messageinthebottle(self, message):
        self.messaga = Gtk.MessageDialog(parent=self.win, flags=Gtk.DialogFlags.MODAL, type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, message_format=(message))
        if self.messaga.run() == Gtk.ResponseType.OK:
            self.messaga.destroy()

    def get_exif(self, file):
        tags2 = ''
        try:
             im = GExiv2.Metadata(file)
             tags_keys = im.get_exif_tags()
             if 'Exif.Image.Model' in tags_keys:
                 tags2 = (_("<i>Model:</i>\t\t\t") + im['Exif.Image.Model'] + "\n")
             if 'Exif.Image.DateTimeOriginal' in tags_keys:
                 tags2 += (_("<i>Date:</i>\t\t\t") + im['Exif.Image.DateTimeOriginal'] + "\n")
             if 'Exif.Photo.FocalLength' in tags_keys:
                 tags2 += (_("<i>Focal length:</i>\t\t") + im['Exif.Photo.FocalLength'] + "mm \n")
             if 'Exif.Photo.FNumber' in tags_keys:
                 tags2 += (_("<i>Aperture:</i>\t\t\tF/") + im['Exif.Photo.FNumber'] + "\n")
             if 'Exif.Photo.ExposureTime' in tags_keys:
                 tags2 += (_("<i>Exposure Time:</i>\t\t") + im['Exif.Photo.ExposureTime'] + " s. \n")
        except IOError:
            print ("failed to identify", file)
        return tags2
               
    def start(self, issend):        
        self.issend = issend
        self.liste_images = []
        self.liste_aligned = []
        index = 0
        for item in self.liststoreimport:
            if item[0]:
               self.liste_images.append(item[1])
               self.liste_aligned.append(settings["preview_folder"] + "/" + settings.align_prefix + format(index, "04d") + ".tif")
               index += 1
        if not Gui.checkbutton_a5_align.get_active():
            self.liste_aligned=self.liste_images
        if self.liste_images.count(self.name):
           self.messageinthebottle(_("Can't overwrite input image!\n\n Please change the output filename."))
           return -1                            
        if len(self.liste_images) <= 1:
            self.messageinthebottle(_("Please add or activate at least two images.\n\n Cannot do anything smart with the one or no image."))
            return -1
        self.update_align_options()
        self.update_enfuse_options()
        ProFus = Progress_Fusion(self.liste_images, self.liste_aligned, self.issend)
        
    def apropos(self, widget):
        self.fen = AproposFen(self.win)
        
    def save_settings(self):
        conf = configparser.ConfigParser()
        conf.add_section('prefs')
        # conf.set('prefs', 'w', self.spinbuttonEdge.get_value_as_int())
        conf.set('prefs', 'pwidth', str(self.spinbuttonlargeurprev.get_value_as_int()))
        conf.set('prefs', 'pheight', str(self.spinbuttonhauteurprev.get_value_as_int()))
        conf.set('prefs', 'cachebutton', str(self.checkbuttoncache.get_active()))
        conf.set('prefs', 'cachesize', str(self.spinbuttoncache.get_value_as_int()))
        conf.set('prefs', 'blocbutton', str(self.checkbuttonbloc.get_active()))
        conf.set('prefs', 'blocsize', str(self.spinbuttonbloc.get_value_as_int()))
        conf.set('prefs', 'outsize', str(self.checkbuttontaillefinale.get_active()))
        conf.set('prefs', 'outwidth', str(self.spinbuttonlargeurfinale.get_value_as_int()))
        conf.set('prefs', 'outheight', str(self.spinbuttonhauteurfinale.get_value_as_int()))
        conf.set('prefs', 'xoff', str(self.spinbuttonxoff.get_value_as_int()))
        conf.set('prefs', 'yoff', str(self.spinbuttonyoff.get_value_as_int()))
        conf.set('prefs', 'jpegdef', str(self.checkbuttonjpegorig.get_active()))
        conf.set('prefs', 'jpegcompr', str(int(self.hscalecomprjpeg.get_value())))
        conf.set('prefs', 'tiffcomp', str(self.combtiff.get_active()))
        conf.set('prefs', 'exif', str(self.checkbuttonexif.get_active()))
        conf.set('prefs', 'alignfiles', str(self.checkbuttonalignfiles.get_active()))
        conf.set('prefs', 'editor',  str(self.entryedit_field.get_text()))
        conf.set('prefs', 'default_folder', settings["default_folder"])
        conf.write(open(settings["config_folder"]+ '/mfusion.cfg', 'w'))
        return

    def pixbuf2Image(self, pb):
        width,height = pb.get_width(),pb.get_height()
        return Image.frombytes("RGB",(width,height),pb.get_pixels() )

    def put_files_to_the_list(self, files):
        self.files = files
        self.tags2 = ''
        self.badfiles = []
        for file in self.files:
            if re.search('\\.jpg$|\\.jpeg$|\\.tiff$|\\.tif$', file, flags=re.IGNORECASE):
                pb = GdkPixbuf.Pixbuf.new_from_file(file)
                im = self.pixbuf2Image(pb)
                self.size = im.size
                # self.tags2 = Gui.get_exif(file)
                if not self.tags2:
                    self.tags2 = ''
                self.tooltip = ("\n" + _("<b>Filename:</b> ") + os.path.basename(file) + "\n"+_("<b>Resolution:</b> ") + str(str(self.size[0]) + "x" + str(self.size[1])) + "\n" + self.tags2)
                self.liststoreimport.append([1, file, GdkPixbuf.Pixbuf.new_from_file_at_size(file, 128, 128), self.tooltip])
            else:
                self.badfiles.append(file)
        if len(self.badfiles)>0:
            message = _("Only JPEG and TIFF files are allowed.\n\nCannot open:\n")
            for itz in self.badfiles:
                message += itz + "\n"
            Gui.messageinthebottle(message)
        return 
        
####################################################################
###########Classe pour choisir les images a fusionner###############
####################################################################
    
class OpenFiles_Dialog:
    """La classe qui ouvre la fenetre de choix de files, et qui retourne le ListStore par la methode get_model"""
    def __init__(self, model, parent):
        """Lance la fenetre de selection et créé la listsore a partir des files selectionnés"""
        self.filter = Gtk.FileFilter()
        self.filter.add_mime_type("image/jpeg")
        self.filter.add_mime_type("image/tiff")
        self.liststoreimport = model #on repart de l'ancien modele

        self.file_dialog = Gtk.FileChooserDialog(_("Add images..."), 
                                                    parent, 
                                                    Gtk.FileChooserAction.OPEN,
                                                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.file_dialog.set_select_multiple(True)
        self.file_dialog.set_current_folder(settings["default_folder"])
        self.file_dialog.set_filter(self.filter)
        self.file_dialog.use_preview = True
        self.previewidget = Gtk.Image()
        self.file_dialog.set_preview_widget(self.previewidget)
        self.file_dialog.connect("update-preview", self.update_thumb_preview, self.previewidget)
                 
        if (self.file_dialog.run() == Gtk.ResponseType.OK):
            self.files = self.file_dialog.get_filenames()
            self.tags2 = ''
            self.badfiles = []
            # TODO: check if resolution of files match!
            (path, file) = os.path.split(self.files[0])
            (filename, ext) = os.path.splitext(file)
            settings["default_file"] = filename+"-fused"+ext
            Gui.put_files_to_the_list(self.files)

        settings["default_folder"] = self.file_dialog.get_current_folder()
        data.update_folders()
        self.file_dialog.destroy()
    
    def update_thumb_preview(self, file_chooser, preview):
        if not self.file_dialog.use_preview:
            return
        filename = file_chooser.get_preview_filename()
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 320, 320)
            self.previewidget.set_from_pixbuf(pixbuf)
            self.have_preview = True
        except:
            self.have_preview = False
        self.file_dialog.set_preview_widget_active(self.have_preview)
        return
                 
    def get_model(self):
        """ Retourne la liststore """
        if self.liststoreimport:
            return self.liststoreimport
        else:
            return None
            
#####################################################################
#########Classe pour la fenetre pour choisir le fichier final########
#####################################################################

class SaveFiles_Dialog:
    """La classe qui ouvre la fenetre de choix pour enregistrer le fichier"""          
    def __init__(self, parent):
        
        self.file_dialog = Gtk.FileChooserDialog(_("Save file..."), 
                                                   parent, 
                                                   Gtk.FileChooserAction.SAVE,
                                                   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        self.file_dialog.set_current_folder(settings["default_folder"])
        self.file_dialog.set_current_name(settings["default_file"])
        self.file_dialog.set_do_overwrite_confirmation(True)
        if (self.file_dialog.run() == Gtk.ResponseType.OK):
            self.resultat = self.file_dialog.get_filename()

        settings["default_folder"] = self.file_dialog.get_current_folder()
        self.file_dialog.destroy()

    def get_name(self):
        try:
            return self.resultat
        except AttributeError:
            return ""

#####################################################################
#########Thread pour la prévisualisation#############################
#####################################################################
            
class Thread_Preview(threading.Thread):
    def __init__(self, taille, liste):
        threading.Thread.__init__ (self)
        self.taille = taille
        self.liste = liste
            
    def run(self):
        images_a_fusionner = []
        images_a_align = []
        index = 0
        for item in self.liste:
            if item[0]:
                chemin_miniature = create_thumbnail(item[1],(int(self.taille[0]), int(self.taille[1])))
                images_a_align.append(chemin_miniature)
                images_a_fusionner.append(settings["preview_folder"] + "/test" + format(index, "04d") + ".tif")
                index += 1
        if (len(images_a_fusionner)) <= 1:
            Gui.messageinthebottle(_("Please add two or more images.\n\n Cannot do anything smart with the one image."))
            return
        if not Gui.checkbutton_a5_align.get_active():
            images_a_fusionner = images_a_align
        if Gui.checkbutton_a5_align.get_active():
            command = ["align_image_stack", "-a", settings["preview_folder"] + "/test"] + data.get_align_options() + images_a_align
            Gui.statusbar.push(15, _(":: Align photos..."))
            preview_process = subprocess.Popen(command, stdout=subprocess.PIPE)
            preview_process.wait()
            Gui.statusbar.pop(15)
        Gui.statusbar.push(15, _(":: Fusing photos..."))
        command = [settings["enfuser"], "-o", settings["preview_folder"] + "/" + "preview.tif"] + data.get_enfuse_options() + images_a_fusionner
        preview_process = subprocess.Popen(command, stdout=subprocess.PIPE)
        preview_process.wait()
        Gui.statusbar.pop(15)
        
        
#######################################################################
#########Fenetre de progression lors de la fusion finale###############
#######################################################################
        
class Progress_Fusion:
    def __init__(self, liste, liste_aligned, issend):
        
        #self.progress = Gtk.glade.XML(fname=UI + "progress.xml", domain=APP)
        self.progress = Gtk.Builder()
        self.progress.add_from_file(UI + "progress.xml") 
        self.progress_win = self.progress.get_object("dialog1")
        self.progress_label = self.progress.get_object("progress_label")
        self.info_label = self.progress.get_object("info_label")
        self.progress_bar = self.progress.get_object("progressbar1")
        self.progress_stop_button = self.progress.get_object("stop_button")
        self.dic1 = { "on_stop_button_clicked"  : self.close_progress, 
                      "on_dialog1_destroy"      : self.close_progress }
        self.progress.connect_signals(self.dic1)        
        self.info_label.set_text(_('Fusion images...'))
       
        self.thread_fusion = Thread_Fusion(liste, liste_aligned, issend)  #On prepare le thread qui va faire tout le boulot
        self.thread_fusion.start()                                     #On le lance
        timer = GObject.timeout_add (100, self.pulsate)
        
    def pulsate(self):
        if self.thread_fusion.isAlive():            #Tant que le thread est en cours, 
            self.progress_bar.set_text(_("Fusion, please wait..."))
            self.progress_bar.pulse()               #on fait pulser la barre
            return True                             #et on renvoie True pour que gobject.timeout recommence
        else:
            self.progress_bar.set_fraction(1)
            self.progress_bar.set_text(_("Fused !"))
            self.close_progress(self)
            return False
            
    def close_progress(self, widget):
        self.progress_win.destroy()
            
            
              
##############################################################################
###########Thread de fusion des vraies images#################################
##############################################################################

class Thread_Fusion(threading.Thread):
    def __init__(self, command_fuse, command_align, liste, liste_aligned, issend):
        threading.Thread.__init__ (self)
        self.command_fuse  = [settings["enfuser"], "-o", self.name] + data.get_align_options() + self.liste_aligned
        self.command_align = ["align_image_stack", '-a', settings["preview_folder"] + '/' + settings.align_prefix] + data.get_align_options() + self.liste_images
        self.issend = issend
        self.liste  = liste
        self.liste_aligned = liste_aligned
        
    def run(self):
        if Gui.checkbutton_a5_align.get_active():            
            align_process = subprocess.Popen(self.command_align, stdout=subprocess.PIPE)
            align_process.wait()
        
            if Gui.checkbuttonalignfiles.get_active():
                # copy aligned files in working folder for further processing by user:
                count = 0
                for file in self.liste:
                    tmp_filename    = self.liste_aligned[count] #settings.align_prefix+str(count).zfill(4)+".tif"
                    (path, file_)   = os.path.split(file)
                    (filename, ext) = os.path.splitext(file_)
                    new_filename    = settings["preview_folder"] + "/" + filename + "_" + settings.align_prefix + ".tif"
                    new_filename_dst = path + "/" + filename + "_" + settings.align_prefix + ".tif"
                    if os.path.exists(new_filename):
                        os.remove(new_filename)
                    shutil.copy(tmp_filename, new_filename)
                    # if user wants to export a fused JPG we also give him aligned JPGs
                    if Gui.name.endswith(('.jpg', '.jpeg', '.JPG', '.JPEG')):
                        command = ["mogrify", "-format", "jpg", "-quality", "100", new_filename ]
                        output  = subprocess.Popen(command).communicate()[0]
                        new_filename = os.path.splitext(new_filename)[0] + ".jpg"
                        
                    if os.path.exists(new_filename_dst):
                        os.remove(new_filename_dst)
                    shutil.move(new_filename, new_filename_dst)
                    count += 1
            
        fusion_process = subprocess.Popen(self.command_fuse, stdout=subprocess.PIPE)
        fusion_process.wait()
        
        if Gui.checkbuttonexif.get_active():
            exif_copy = subprocess.Popen(["exiftool", "-tagsFromFile", Gui.liste_images[0], "-overwrite_original", Gui.name])
            exif_copy.wait()
        if len(self.issend) > 0:
            subprocess.Popen([Gui.entryedit_field.get_text(), self.issend], stdout=subprocess.PIPE)


########################################    
#### Classe de la fenêtre a propos  ####
########################################  

class AproposFen:
    def __init__(self, parent):
        self.aboutdialog = Gtk.AboutDialog("About", parent)
        self.aboutdialog.set_name("MacroFusion")
        self.aboutdialog.set_modal(True)
        self.aboutdialog.set_position(Gtk.WindowPosition.CENTER)
        self.aboutdialog.set_version(__VERSION__)
        self.aboutdialog.set_comments('A GTK Gui for the excellent Enfuse.\n\n2014 (c) Dariusz Duma\n<dhor@toxic.net.pl>')
        # self.aboutdialog.set_copyright(__COPYRIGHT__)
        self.aboutdialog.set_website(__WEBSITE__)
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(IMG + "macrofusion.png")
        self.aboutdialog.set_logo(self.pixbuf)
        self.aboutdialog.connect("response", self.close_about)
        self.aboutdialog.show()
        
    def close_about(self, widget, event):
        self.aboutdialog.destroy()

        
###########################################################    
####  Initialisation et appel de la classe principale  ####
###########################################################            
                        
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    data = data()                                              
    Gui  = Interface()
                               
    if (len(sys.argv)>1):     
        files = sys.argv[1:]
        Gui.put_files_to_the_list(files)
#        if len(Gui.liststoreimport) == 0:
#            Gui.messageinthebottle(_("\nCan work only with JPEG or TIFF files."))

    Gtk.main()

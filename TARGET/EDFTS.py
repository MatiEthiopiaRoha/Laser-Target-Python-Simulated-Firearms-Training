from canvas_manager import CanvasManager
import configurator
from configurator import Configurator
import cv2
import glob
import imp
import numpy
import os
from PIL import Image, ImageTk
from preferences_editor import PreferencesEditor
import re
from shot import Shot
from tag_parser import TagParser
from target_editor import TargetEditor
from target_pickler import TargetPickler
import time
from training_protocols.protocol_operations import ProtocolOperations
from threading import Thread
import Tkinter, tkFileDialog, tkMessageBox, ttk

FEED_FPS = 30  # ms
SHOT_MARKER = "shot_marker"
TARGET_VISIBILTY_MENU_INDEX = 3

DEFAULT_SHOT_LIST_COLUMNS = ("Time", "Laser")


class MainWindow:
    def refresh_frame(self, *args):
        rval, self._webcam_frame = self._cv.read()

        if (rval == False):
            self._refresh_miss_count += 1
            self.logger.debug ("Missed %d webcam frames." +
                "will stop processing shots.", self._refresh_miss_count)

            if self._refresh_miss_count >= 25:
                tkMessageBox.showerror("Webcam Disconnected", "Missed too many " +
                    "webcam frames. The camera is probably disconnected so " +
                    "EDFTS will stop processing shots.")
                self.logger.critical("Missed %d webcam frames. The camera is probably " +
                    "disconnected so EDFTS will stop processing shots.",
                    self._refresh_miss_count)
                self._shutdown = True
            else:
                if self._shutdown == False:
                    self._window.after(FEED_FPS, self.refresh_frame)

            return

        self._refresh_miss_count = 0

   
        webcam_image = cv2.cvtColor(self._webcam_frame, cv2.cv.CV_BGR2RGB)

        
        if self._show_interference:
            if self._interference_iterations > 0:
                self._interference_iterations -= 1

                frame_bw = cv2.cvtColor(self._webcam_frame, cv2.cv.CV_BGR2GRAY)
                (thresh, webcam_image) = cv2.threshold(frame_bw,
                    self._preferences[configurator.LASER_INTENSITY], 255,
                    cv2.THRESH_BINARY)

        
        self._image = ImageTk.PhotoImage(image=Image.fromarray(webcam_image))

        
        self._editor_image = ImageTk.PhotoImage(
            image=Image.fromarray(webcam_image))

        webcam_image = self._webcam_canvas.create_image(0, 0, image=self._image,
            anchor=Tkinter.NW, tags=("background"))

        if self._show_targets:
           
            for target in self._targets:
                self._webcam_canvas.tag_raise(target)
            self._webcam_canvas.tag_raise(SHOT_MARKER)
            self._webcam_canvas.tag_lower(webcam_image)
        else:
     
            self._webcam_canvas.tag_raise(SHOT_MARKER)
            self._webcam_canvas.tag_lower(webcam_image)
            for target in self._targets:
                self._webcam_canvas.tag_lower(target)

        if self._shutdown == False:
            self._window.after(FEED_FPS, self.refresh_frame)

    def detect_shots(self):
        if (self._webcam_frame is None):
            self._window.after(self._preferences[configurator.DETECTION_RATE], self.detect_shots)
            return

        frame_bw = cv2.cvtColor(self._webcam_frame, cv2.cv.CV_BGR2GRAY)

     
        (thresh, frame_thresh) = cv2.threshold(frame_bw, 
            self._preferences[configurator.LASER_INTENSITY], 255, cv2.THRESH_BINARY)

        if not self._seen_interference:
            self.detect_interfence(frame_thresh)


        min_max = cv2.minMaxLoc(frame_thresh)

        if (min_max[0] != min_max[1]):
            x = min_max[3][0]
            y = min_max[3][1]

            laser_color = self.detect_laser_color(x, y)

           
           
            if (laser_color is not None and
                self._preferences[configurator.IGNORE_LASER_COLOR] not in laser_color):

                self.handle_shot(laser_color, x, y)

        if self._shutdown == False:
            self._window.after(self._preferences[configurator.DETECTION_RATE],
                self.detect_shots)

    def handle_shot(self, laser_color, x, y):
        timestamp = 0

        
        if self._shot_timer_start is None:
            self._shot_timer_start = time.time()
        else:
            timestamp = time.time() - self._shot_timer_start

        tree_item = None

        if "green" in laser_color:
            tree_item = self._shot_timer_tree.insert("", "end",
                values=[timestamp, "green"])
        else:
            tree_item = self._shot_timer_tree.insert("", "end",
                values=[timestamp, laser_color])
        self._shot_timer_tree.see(tree_item)

        new_shot = Shot((x, y), self._webcam_canvas,
            self._preferences[configurator.MARKER_RADIUS],
            laser_color, timestamp)
        self._shots.append(new_shot)
        new_shot.draw_marker()

        
        self.process_hit(new_shot, tree_item)

    def detect_interfence(self, image_thresh):
        brightness_hist = cv2.calcHist([image_thresh], [0], None, [256], [0, 255])
        percent_dark = brightness_hist[0] / image_thresh.size


        if (percent_dark < .99):
            
            self._seen_interference = True

            self.logger.warning(
                "Glare or light source detected. %f of the image is dark." %
                percent_dark)

            self._show_interference = tkMessageBox.askyesno("Interference Detected", "Bright glare or a light source has been detected on the webcam feed, which will interfere with shot detection. Do you want to see a feed where the interference will be white and everything else will be black for a short period of time?")

            if self._show_interference:
               
                self._interference_iterations = 2500 / FEED_FPS

    def detect_laser_color(self, x, y):
        
        l = self._webcam_frame.shape[1]
        h = self._webcam_frame.shape[0]
        mask = numpy.zeros((h, l, 1), numpy.uint8)
        cv2.circle(mask, (x, y), 10, (255, 255, 555), -1)
        mean_color = cv2.mean(self._webcam_frame, mask)

       
        r = mean_color[2]
        g = mean_color[1]
        b = mean_color[0]

        if (r > g) and (r > b):
            return "red"

        if (g > r) and (g > b):
            return "green2"

        return None

    def process_hit(self, shot, shot_list_item):
        is_hit = False

        x = shot.get_coords()[0]
        y = shot.get_coords()[1]

        regions = self._webcam_canvas.find_overlapping(x, y, x, y)

     
        for region in reversed(regions):
            tags = TagParser.parse_tags(
                self._webcam_canvas.gettags(region))

            if "_internal_name" in tags and "command" in tags:
                self.execute_region_commands(tags["command"])

            if "_internal_name" in tags and self._loaded_training != None:
                self._loaded_training.hit_listener(region, tags, shot, shot_list_item)

            if "_internal_name" in tags:
                is_hit = True
               
                break

        if self._loaded_training != None:
            self._loaded_training.shot_listener(shot, shot_list_item, is_hit)

    def open_target_editor(self):
        TargetEditor(self._frame, self._editor_image,
                     notifynewfunc=self.new_target_listener)

    def add_target(self, name):
       
        target_name = "_internal_name:target" + str(self._target_count)
        self._target_count += 1

        target_pickler = TargetPickler()
        (region_object, regions) = target_pickler.load(
            name, self._webcam_canvas, target_name)

        self._targets.append(target_name)

    def edit_target(self, name):
        TargetEditor(self._frame, self._editor_image, name,
                     self.new_target_listener)

    def new_target_listener(self, target_file):
        (root, ext) = os.path.splitext(os.path.basename(target_file))
        self._add_target_menu.add_command(label=root,
                command=self.callback_factory(self.add_target,
                target_file))
        self._edit_target_menu.add_command(label=root,
                command=self.callback_factory(self.edit_target,
                target_file))

    def execute_region_commands(self, command_list):
        args = []

        for command in command_list:
        
            pattern = r'(\w[\w\d_]*)\((.*)\)$'
            match = re.match(pattern, command)
            if match:
                command = match.groups()[0]
                if len(match.groups()) > 0:
                    args = match.groups()[1].split(",")

          
            if command == "clear_shots":
                self.clear_shots()

            if command == "play_sound":
                self._protocol_operations.play_sound(args[0])

    def toggle_target_visibility(self):
        if self._show_targets:
            self._targets_menu.entryconfig(TARGET_VISIBILTY_MENU_INDEX,
                label="Show Targets")
        else:
            self._targets_menu.entryconfig(TARGET_VISIBILTY_MENU_INDEX,
                label="Hide Targets")

        self._show_targets = not self._show_targets

    def clear_shots(self):
        self._webcam_canvas.delete(SHOT_MARKER)
        self._shots = []

        if self._loaded_training != None:
            self._loaded_training.reset(self.aggregate_targets())

        self._shot_timer_start = None
        shot_entries = self._shot_timer_tree.get_children()
        for shot in shot_entries: self._shot_timer_tree.delete(shot)
        self._previous_shot_time_selection = None

        self._webcam_canvas.focus_set()

    def quit(self):
        self._shutdown = True
        self._cv.release()
        self._window.quit()

    def canvas_click_red(self, event):
        if self._preferences[configurator.DEBUG]:
            self.handle_shot("red", event.x, event.y)

    def canvas_click_green(self, event):
        if self._preferences[configurator.DEBUG]:
            self.handle_shot("green", event.x, event.y)

    def canvas_click(self, event):
      
        selected_region = event.widget.find_closest(
            event.x, event.y)
        target_name = ""

        for tag in self._webcam_canvas.gettags(selected_region):
            if tag.startswith("_internal_name:"):
                target_name = tag
                break

        if self._selected_target == target_name:
            return

        self._canvas_manager.selection_update_listener(self._selected_target,
                                                       target_name)
        self._selected_target = target_name

    def canvas_delete_target(self, event):
        if (self._selected_target):
            for target in self._targets:
                if target == self._selected_target:
                    self._targets.remove(target)
            event.widget.delete(self._selected_target)
            self._selected_target = ""

    def cancel_training(self):
        if self._loaded_training:
            self._loaded_training.destroy()
            self._protocol_operations.destroy()
            self._loaded_training = None

    def aggregate_targets(self):
       
        targets = []

        for target in self._targets:
            target_regions = self._webcam_canvas.find_withtag(target)
            target_data = {"name": target, "regions": []}
            targets.append(target_data)

            for region in target_regions:
                tags = TagParser.parse_tags(
                    self._webcam_canvas.gettags(region))
                target_data["regions"].append(tags)

        return targets

    def load_training(self, plugin):
        targets = self.aggregate_targets()

        if self._loaded_training:
            self._loaded_training.destroy()

        if self._protocol_operations:
            self._protocol_operations.destroy()

        self._protocol_operations = ProtocolOperations(self._webcam_canvas, self)
        self._loaded_training = imp.load_module("__init__", *plugin).load(
            self._protocol_operations, targets)

    def edit_preferences(self):
        preferences_editor = PreferencesEditor(self._window, self._config_parser,
                                               self._preferences)

    def which(self, program):
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file

        return None

    def save_feed_image(self):
       
        filetypes = []

        if (self.which("gs") is None and self.which("gswin32c.exe") is None
            and self.which("gswin64c.exe") is None):
            filetypes=[("Encapsulated PostScript", "*.eps")]
        else:
           filetypes=[("Portable Network Graphics", "*.png"),
                ("Encapsulated PostScript", "*.eps"),
                ("GIF", "*.gif"), ("JPEG", "*.jpeg")]

        image_file = tkFileDialog.asksaveasfilename(
            filetypes=filetypes,
            title="Save EDFTS Webcam Feed",
            parent=self._window)

        if not image_file: return

        file_name, extension = os.path.splitext(image_file)

      
        if ".eps" not in extension:
            self._webcam_canvas.postscript(file=(file_name + "tmp.eps"))
            img = Image.open(file_name + "tmp.eps", "r")
            img.save(image_file, extension[1:])
            del img
            os.remove(file_name + "tmp.eps")
        else:
            self._webcam_canvas.postscript(file=(file_name + ".eps"))

    def shot_time_selected(self, event):
        selected_shots = event.widget.focus()
        shot_index = event.widget.index(selected_shots)
        self._shots[shot_index].toggle_selected()

        if self._previous_shot_time_selection is not None:
            self._previous_shot_time_selection.toggle_selected()

        self._previous_shot_time_selection = self._shots[shot_index]

        self._webcam_canvas.focus_set()

    def configure_default_shot_list_columns(self):
        self.configure_shot_list_columns(DEFAULT_SHOT_LIST_COLUMNS, [50, 50])

    def add_shot_list_columns(self, id_list):
        current_columns = self._shot_timer_tree.cget("columns")
        if not current_columns:
            self._shot_timer_tree.configure(columns=(id_list))
        else:
            self._shot_timer_tree.configure(columns=(current_columns + id_list))

    def resize_shot_list(self):
        self._shot_timer_tree.configure(displaycolumns="#all")

  
    def revert_shot_list_columns(self):
        self._shot_timer_tree.configure(columns=DEFAULT_SHOT_LIST_COLUMNS)
        self.configure_default_shot_list_columns()

        shot_entries = self._shot_timer_tree.get_children()
        for shot in shot_entries:
            current_values = self._shot_timer_tree.item(shot, "values")
            default_values = current_values[0:len(DEFAULT_SHOT_LIST_COLUMNS)]
            self._shot_timer_tree.item(shot, values=default_values)

        self.resize_shot_list()

    def configure_shot_list_columns(self, names, widths):
        for name, width in zip(names, widths):
            self.configure_shot_list_column(name, width)

        self.resize_shot_list()

    def append_shot_list_column_data(self, item, values):
        current_values = self._shot_timer_tree.item(item, "values")
        self._shot_timer_tree.item(item, values=(current_values + values))

    def configure_shot_list_column(self, name, width):
        self._shot_timer_tree.heading(name, text=name)
        self._shot_timer_tree.column(name, width=width, stretch=False)

    def build_gui(self, feed_dimensions=(600, 480)):
        
        self._window = Tkinter.Tk()
        self._window.protocol("WM_DELETE_WINDOW", self.quit)
        self._window.title("Ethiopian Defense Force AI LASER SHOOT TARGET System")

        self._frame = ttk.Frame(self._window)
        self._frame.pack()

        
        self._webcam_canvas = Tkinter.Canvas(self._frame,
            width=feed_dimensions[0], height=feed_dimensions[1])
        self._webcam_canvas.grid(row=0, column=0)

        self._webcam_canvas.bind('<ButtonPress-1>', self.canvas_click)
        self._webcam_canvas.bind('<Delete>', self.canvas_delete_target)
    
        if self._preferences[configurator.DEBUG]:
            self._webcam_canvas.bind('<Shift-ButtonPress-1>', self.canvas_click_red)
            self._webcam_canvas.bind('<Control-ButtonPress-1>', self.canvas_click_green)

        self._canvas_manager = CanvasManager(self._webcam_canvas)

    
        self._clear_shots_button = ttk.Button(
            self._frame, text="Clear Shots", command=self.clear_shots)
        self._clear_shots_button.grid(row=1, column=0)

    
        self._shot_timer_tree = ttk.Treeview(self._frame, selectmode="browse",
                                             show="headings")
        self.add_shot_list_columns(DEFAULT_SHOT_LIST_COLUMNS)
        self.configure_default_shot_list_columns()

        tree_scrolly = ttk.Scrollbar(self._frame, orient=Tkinter.VERTICAL,
                                     command=self._shot_timer_tree.yview)
        self._shot_timer_tree['yscroll'] = tree_scrolly.set

        tree_scrollx = ttk.Scrollbar(self._frame, orient=Tkinter.HORIZONTAL,
                                     command=self._shot_timer_tree.xview)
        self._shot_timer_tree['xscroll'] = tree_scrollx.set

        self._shot_timer_tree.grid(row=0, column=1, rowspan=2, sticky=Tkinter.NSEW)
        tree_scrolly.grid(row=0, column=2, rowspan=2, stick=Tkinter.NS)
        tree_scrollx.grid(row=1, column=1, stick=Tkinter.EW)
        self._shot_timer_tree.bind("<<TreeviewSelect>>", self.shot_time_selected)

        self.create_menu()

    def create_menu(self):
        menu_bar = Tkinter.Menu(self._window)
        self._window.config(menu=menu_bar)

        file_menu = Tkinter.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Preferences", command=self.edit_preferences)
        file_menu.add_command(label="Save Feed Image...", command=self.save_feed_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

     
        self._targets_menu = Tkinter.Menu(menu_bar, tearoff=False)
        self._targets_menu.add_command(label="Create Target...",
            command=self.open_target_editor)
        self._add_target_menu = self.create_target_list_menu(
            self._targets_menu, "Add Target", self.add_target)
        self._edit_target_menu = self.create_target_list_menu(
            self._targets_menu, "Edit Target", self.edit_target)
        self._targets_menu.add_command(label="Hide Targets",
            command=self.toggle_target_visibility)
        menu_bar.add_cascade(label="Targets", menu=self._targets_menu)

        training_menu = Tkinter.Menu(menu_bar, tearoff=False)

       
        self._training_selection = Tkinter.StringVar()
        name = "None"
        training_menu.add_radiobutton(label=name, command=self.cancel_training,
                variable=self._training_selection, value=name)
        self._training_selection.set(name)

        self.create_training_list(training_menu, self.load_training)
        menu_bar.add_cascade(label="Training", menu=training_menu)

    def callback_factory(self, func, name):
        return lambda: func(name)

    def create_target_list_menu(self, menu, name, func):
        targets = glob.glob("targets/*.target")

        target_list_menu = Tkinter.Menu(menu, tearoff=False)

        for target in targets:
            (root, ext) = os.path.splitext(os.path.basename(target))
            target_list_menu.add_command(label=root,
                command=self.callback_factory(func, target))

        menu.add_cascade(label=name, menu=target_list_menu)

        return target_list_menu

    def create_training_list(self, menu, func):
        protocols_dir = "training_protocols"

        plugin_candidates = os.listdir(protocols_dir)
        for candidate in plugin_candidates:
            plugin_location = os.path.join(protocols_dir, candidate)
            if (not os.path.isdir(plugin_location) or
                not "__init__.py" in os.listdir(plugin_location)):
                continue
            plugin_info = imp.find_module("__init__", [plugin_location])
            training_info = imp.load_module("__init__", *plugin_info).get_info()
            menu.add_radiobutton(label=training_info["name"],
                command=self.callback_factory(self.load_training, plugin_info),
                variable=self._training_selection, value=training_info["name"])

    def __init__(self, config):
        self._shots = []
        self._targets = []
        self._target_count = 0
        self._refresh_miss_count = 0
        self._show_targets = True
        self._selected_target = ""
        self._loaded_training = None
        self._seen_interference = False
        self._show_interference = False
        self._webcam_frame = None
        self._config_parser = config.get_config_parser()
        self._preferences = config.get_preferences()
        self._shot_timer_start = None
        self._previous_shot_time_selection = None
        self.logger = config.get_logger()

        self._cv = cv2.VideoCapture(0)

        if self._cv.isOpened():
            width = self._cv.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)
            height = self._cv.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)

 
            if width < 640 and height < 480:
                self.logger.info("Webcam resolution is current low (%dx%d), " +
                                 "attempting to increase it to 640x480", width, height)
                self._cv.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 640)
                self._cv.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 480)
                width = self._cv.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)
                height = self._cv.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)

            self.logger.debug("Webcam resolution is %dx%d", width, height)
            self.build_gui((width, height))
            self._protocol_operations = ProtocolOperations(self._webcam_canvas, self)

            fps = self._cv.get(cv2.cv.CV_CAP_PROP_FPS)
            if fps <= 0:
                self.logger.info("Couldn't get webcam FPS, defaulting to 30.")
            else:
                FEED_FPS = fps
                self.logger.info("Feed FPS set to %d.", fps)

            
            self._shutdown = False

        else:
            tkMessageBox.showerror("Couldn't Connect to Webcam", "Video capturing " +
                "could not be initialized either because there is no webcam or " +
                "we cannot connect to it. EDFTS will shut down.")
            self.logger.critical("Video capturing could not be initialized either " +
                "because there is no webcam or we cannot connect to it.")
            self._shutdown = True

    def main(self):

        self._refresh_thread = Thread(target=self.refresh_frame, name="refresh_thread")
        self._refresh_thread.start()

        self._shot_detection_thread = Thread(target=self.detect_shots, name="shot_detection_thread")
        self._shot_detection_thread.start()
        if not self._shutdown:
            Tkinter.mainloop()
            self._window.destroy()

if __name__ == "__main__":

    mainWindow = MainWindow(Configurator())
    mainWindow.main()

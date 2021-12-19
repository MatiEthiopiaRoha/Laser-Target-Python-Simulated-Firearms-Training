from canvas_manager import CanvasManager
import os
from PIL import Image, ImageTk
from tag_editor_popup import TagEditorPopup
from target_pickler import TargetPickler
import Tkinter, tkFileDialog, tkMessageBox, ttk

CURSOR = 0
RECTANGLE = 1
OVAL = 2
TRIANGLE = 3
FREEFORM_POLYGON = 4

CANVAS_BACKGROUND = (1,)

class TargetEditor():
    def save_target(self):
        target_file = tkFileDialog.asksaveasfilename(
            defaultextension=".target",
            filetypes=[("EDFTS Target", ".target")],
            initialdir="targets/",
            title="Save EDFTS Target",
            parent=self._window)

        is_new_target = target_file and not os.path.isfile(target_file)

        if target_file:
            target_pickler = TargetPickler()
            target_pickler.save(target_file, self._regions,
                self._target_canvas)

        if (is_new_target):
            self._notify_new_target(target_file)

    def color_selected(self, event):
        self._target_canvas.focus_set()

        if (self._selected_region is not None and
            self._selected_region != CANVAS_BACKGROUND):               

            self._target_canvas.itemconfig(self._selected_region,
                fill=self._fill_color_combo.get())

    def bring_forward(self):
        if (self._selected_region is not None and
            self._selected_region != CANVAS_BACKGROUND):
            
            below = self._target_canvas.find_above(self._selected_region)
            
            if len(below) > 0:
                self._target_canvas.tag_raise(self._selected_region,
                    below)

                
                self.reverse_regions(below, self._selected_region)

    def send_backward(self):
        if (self._selected_region is not None and
            self._selected_region != CANVAS_BACKGROUND):
            
            above = self._target_canvas.find_below(self._selected_region)

            if len(above) > 0  and above != CANVAS_BACKGROUND:
                self._target_canvas.tag_lower(self._selected_region,
                    above)

                
                self.reverse_regions(above, self._selected_region)

    def reverse_regions(self, region1, region2):
        r1 = self._regions.index(region1[0])
        r2 = self._regions.index(region2[0])

        self._regions[r2], self._regions[r1] = self._regions[r1], self._regions[r2]

    def undo_vertex(self, event):
        if self._radio_selection.get() == FREEFORM_POLYGON:
      
            if len(self._freeform_vertices_ids) > 0:
                self._target_canvas.delete(self._freeform_vertices_ids[-1])
                del self._freeform_vertices_points[-1]
                del self._freeform_vertices_ids[-1]           

            if len(self._freeform_edges_ids) > 0:
                self._target_canvas.delete(self._freeform_edges_ids[-1])
                del self._freeform_edges_ids[-1]

            if self._freeform_temp_line_id is not None:
                self._target_canvas.delete(self._freeform_temp_line_id)
                self._freeform_temp_line_id = None

    def _reset_freeform_polygon(self):
        self._target_canvas.delete("_shape:vertex")
        self._target_canvas.delete("_shape:freeform_edge")

        self._freeform_vertices_points = []
        self._freeform_vertices_ids = []
        self._freeform_edges_ids = []
        self._freeform_temp_line_id = None

    def radio_button_click(self):
        if self._radio_selection.get() != FREEFORM_POLYGON:
            self._reset_freeform_polygon()

    def canvas_right_click(self, event):
        if self._radio_selection.get() == FREEFORM_POLYGON:
            if len(self._freeform_vertices_points) < 4:
                tkMessageBox.showerror("Invalid Regular Polygon",
                    "A freeform polygon must have at least 3 vertices and should be " +
                    "closed.",
                    parent=self._frame)
                return

  
            self._freeform_vertices_points[-1] = self._freeform_vertices_points[0]


            self._freeform_region = self._target_canvas.create_polygon(
                self._freeform_vertices_points,
                fill="black", outline="black", stipple="gray25",
                tags=("_shape:freeform_polygon"))
            self._regions.append(self._freeform_region)
            self._create_cursor_shape(event)

           
            self._reset_freeform_polygon()

    def canvas_click(self, event):
        if self._radio_selection.get() == FREEFORM_POLYGON:
            self._freeform_vertices_points.append((event.x, event.y))
            self._freeform_vertices_ids.append(self._cursor_shape)

            if self._freeform_temp_line_id is not None:
                self._freeform_edges_ids.append(self._freeform_temp_line_id)

            self._create_cursor_shape(event)

        elif self._radio_selection.get() != CURSOR:
     
            self._regions.append(self._cursor_shape)
            self._create_cursor_shape(event)
        else:
            old_region = self._selected_region
            self._selected_region = event.widget.find_closest(
                event.x, event.y)  

            self._canvas_manager.selection_update_listener(old_region,
                self._selected_region)

            if self._selected_region != CANVAS_BACKGROUND:
                self._fill_color_combo.configure(state="readonly") 
                self._fill_color_combo.set(
                    event.widget.itemcget(self._selected_region, "fill"))

                self._tags_button.configure(state=Tkinter.NORMAL)

                if self._tag_popup_state.get()==True:
                    self.toggle_tag_editor()
            else:
                self._fill_color_combo.configure(state=Tkinter.DISABLED)  
                self._tags_button.configure(state=Tkinter.DISABLED)  

                if self._tag_popup_state.get()==True:
                    self._tag_popup_state.set(False)
                    self.toggle_tag_editor()

    def canvas_mouse_move(self, event):
        if self._cursor_shape is not None:
            self._target_canvas.delete(self._cursor_shape)

        if self._freeform_temp_line_id is not None:
            self._target_canvas.delete(self._freeform_temp_line_id)
        
        if self._radio_selection.get() == CURSOR:
            self._cursor_shape = None

        self._create_cursor_shape(event)

    def _create_cursor_shape(self, event):
        initial_size = 30

        if self._radio_selection.get() == RECTANGLE:        
            self._cursor_shape = self._target_canvas.create_rectangle(
                event.x - initial_size,
                event.y - initial_size,
                event.x + initial_size,
                event.y + initial_size, 
                fill="black", stipple="gray25", tags=("_shape:rectangle"))

        elif self._radio_selection.get() == OVAL:        
            self._cursor_shape = self._target_canvas.create_oval(
                event.x - initial_size,
                event.y - initial_size,
                event.x + initial_size,
                event.y + initial_size, 
                fill="black", stipple="gray25", tags=("_shape:oval"))

        elif self._radio_selection.get() == TRIANGLE:        
            self._cursor_shape = self._target_canvas.create_polygon(
                event.x,
                event.y - initial_size,
                event.x + initial_size,
                event.y + initial_size,
                event.x - initial_size,
                event.y + initial_size, 
                event.x,
                event.y - initial_size,
                fill="black", outline="black", stipple="gray25",
                tags=("_shape:triangle"))

        elif self._radio_selection.get() == FREEFORM_POLYGON:     
            
            vertex_size = 2
   
            self._cursor_shape = self._target_canvas.create_oval(
                event.x - vertex_size,
                event.y - vertex_size,
                event.x + vertex_size,
                event.y + vertex_size, 
                fill="black", tags=("_shape:vertex"))

           
            if len(self._freeform_vertices_points) > 0:
                last_point = self._freeform_vertices_points[-1]

                self._freeform_temp_line_id = self._target_canvas.create_line(
                    last_point,
                    event.x, event.y,
                    dash=(4,4), tags="_shape:freeform_edge")

    def canvas_delete_region(self, event):
        if (self._selected_region is not None and
            self._selected_region != CANVAS_BACKGROUND):
            
            for shape in self._selected_region:
                self._regions.remove(shape)
            event.widget.delete(self._selected_region)
            self._selected_region = None

    def toggle_tag_editor(self):
        if self._tag_popup_state.get()==True:
            x = (self._tags_button.winfo_x() + 
                (self._tags_button.winfo_width() / 2))
            y = (self._tags_button.winfo_y() +
                (self._tags_button.winfo_height() * 1.5))

            self._tag_editor.show(
                self._target_canvas.gettags(self._selected_region), x, y)
        else:
            self._tag_editor.hide()

    def update_tags(self, new_tag_list):
        
        for tag in self._target_canvas.gettags(self._selected_region):
            if not tag.startswith("_"):
                self._target_canvas.dtag(self._selected_region,
                   tag)
       
        tags = self._target_canvas.gettags(self._selected_region)
        self._target_canvas.itemconfig(self._selected_region, 
            tags=tags + new_tag_list)

    def build_gui(self, parent, webcam_image):

        self._window = Tkinter.Toplevel(parent)
        self._window.transient(parent)
        self._window.title("Target Editor")

        self._frame = ttk.Frame(self._window)
        self._frame.pack(padx=15, pady=15)

        self.create_toolbar(self._frame)

        self._tag_editor = TagEditorPopup(self._window, self.update_tags)


        self._webcam_image = webcam_image

        self._target_canvas = Tkinter.Canvas(self._frame, 
            width=webcam_image.width(), height=webcam_image.height()) 
        self._target_canvas.create_image(0, 0, image=self._webcam_image,
            anchor=Tkinter.NW, tags=("background"))
        self._target_canvas.pack()

        self._target_canvas.bind('<ButtonPress-1>', self.canvas_click)
        self._target_canvas.bind('<Motion>', self.canvas_mouse_move)
        self._target_canvas.bind('<Delete>', self.canvas_delete_region)
        self._target_canvas.bind('<Control-z>', self.undo_vertex)
        self._target_canvas.bind('<ButtonPress-3>', self.canvas_right_click)

        self._canvas_manager = CanvasManager(self._target_canvas)

      
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()

        self._window.geometry("+%d+%d" % (parent_x+20, parent_y+20))

    def create_toolbar(self, parent):
      
        toolbar = Tkinter.Frame(parent, bd=1, relief=Tkinter.RAISED)
        self._radio_selection = Tkinter.IntVar()
        self._radio_selection.set(CURSOR)


        self._save_icon = Image.open("images/gnome_media_floppy.png")
        self.create_toolbar_button(toolbar, self._save_icon, 
            self.save_target)
        
       
        self._cursor_icon = Image.open("images/cursor.png")
        self.create_radio_button(toolbar, self._cursor_icon, CURSOR)

     
        self._rectangle_icon = Image.open("images/rectangle.png")
        self.create_radio_button(toolbar, self._rectangle_icon, RECTANGLE)

      
        self._oval_icon = Image.open("images/oval.png")
        self.create_radio_button(toolbar, self._oval_icon, OVAL)

    
        self._triangle_icon = Image.open("images/triangle.png")
        self.create_radio_button(toolbar, self._triangle_icon, TRIANGLE)

        
        self._freeform_polygon_icon = Image.open("images/freeform_polygon.png")
        self.create_radio_button(toolbar, self._freeform_polygon_icon, FREEFORM_POLYGON)

        
        self._bring_forward_icon = Image.open("images/bring_forward.png")
        self.create_toolbar_button(toolbar, self._bring_forward_icon, 
            self.bring_forward)

       
        self._send_backward_icon = Image.open("images/send_backward.png")
        self.create_toolbar_button(toolbar, self._send_backward_icon, 
            self.send_backward)

      
        tags_icon = ImageTk.PhotoImage(Image.open("images/tags.png"))  

        self._tag_popup_state = Tkinter.IntVar()
        self._tags_button = Tkinter.Checkbutton(toolbar,
            image=tags_icon, indicatoron=False, variable=self._tag_popup_state,
            command=self.toggle_tag_editor, state=Tkinter.DISABLED)
        self._tags_button.image = tags_icon
        self._tags_button.pack(side=Tkinter.LEFT, padx=2, pady=2)

       
        self._fill_color_combo = ttk.Combobox(toolbar,
            values=["black", "blue", "green", "orange", "red", "white"],
            state="readonly")
        self._fill_color_combo.set("black")
        self._fill_color_combo.bind("<<ComboboxSelected>>", self.color_selected)
        self._fill_color_combo.configure(state=Tkinter.DISABLED)
        self._fill_color_combo.pack(side=Tkinter.LEFT, padx=2, pady=2)

        toolbar.pack(fill=Tkinter.X)

    def create_radio_button(self, parent, image, selected_value):
        icon = ImageTk.PhotoImage(image)  

        button = Tkinter.Radiobutton(parent, image=icon,              
            indicatoron=False, variable=self._radio_selection,
            value=selected_value, command=self.radio_button_click)
        button.image = icon
        button.pack(side=Tkinter.LEFT, padx=2, pady=2)

    def create_toolbar_button(self, parent, image, command, enabled=True):
        icon = ImageTk.PhotoImage(image)  

        button = Tkinter.Button(parent, image=icon, relief=Tkinter.RAISED, command=command)

        if not enabled:
            button.configure(state=Tkinter.DISABLED)

        button.image = icon
        button.pack(side=Tkinter.LEFT, padx=2, pady=2)

  
    def __init__(self, parent, webcam_image, target=None,
        notifynewfunc=None):

        self._cursor_shape = None
        self._selected_region = None
        self._regions = []
        self._freeform_vertices_points = []
        self._freeform_vertices_ids = []
        self._freeform_edges_ids = []
        self._freeform_temp_line_id = None
        self.build_gui(parent, webcam_image)

        if target is not None:
            target_pickler = TargetPickler()
            (region_object, self._regions) = target_pickler.load(
                target, self._target_canvas)

        self._notify_new_target = notifynewfunc

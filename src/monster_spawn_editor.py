import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw
import os
import re
import sys
import shutil
import traceback
import copy  # For deep copying spawns for undo/redo functionality

APP_VERSION = "1.03"

# Pillow < 9.1 has no Image.Resampling
LANCZOS = getattr(Image, "Resampling", Image).LANCZOS

# Sections of a MonsterSetBase file: the number on its own line before each block -> (name, map colour)
SECTIONS = {
    0: ("NPCs", "yellow"),
    1: ("Area spawns", "#3d8bff"),
    2: ("Single spots", "red"),
    3: ("Random areas", "#33cc33"),
    4: ("Event spawns", "cyan"),
}
# Sections whose lines carry an end position and a quantity (the others only have one position)
AREA_SECTIONS = (1, 3)
SECTION_CHOICES = ["Auto"] + [f"{number} - {name}" for number, (name, _) in SECTIONS.items()]
SECTION_SEPARATOR = "//" + "=" * 137

class MonsterSpawnEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Monster & MonsterSetBase Editor by Shizoo")
        
        # Set program icon if available
        self.set_program_icon()
        
        # Initialize undo/redo stacks (each map keeps its own history in map_history)
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 50  # Maximum number of actions to keep in history
        self.map_history = {}
        
        # Dictionary to store spawns for each map
        self.map_spawns = {}
        self.modified_maps = set()  # Track which maps have been modified
        self.backed_up_files = set()  # Files already copied to .bak in this session

        # Current selections
        self.selected_map_file = None
        self.selected_monster_id = None  # Monster used for new spawns
        self.stats_monster_id = None     # Monster shown in the stats panel
        self.selected_spawn_index = -1
        self.spawns = []
        self.map_files = []
        self.map_list_rows = []    # Map file shown in each row of the map list
        self.spawn_list_rows = []  # Spawn index shown in each row of the spawn list (None for headers)
        self.visible_spawn_indices = set()

        # Selection rectangle variables
        self.start_x = None
        self.start_y = None
        self.selection_rect = None
        self.is_selecting = False

        # Dragging an existing spawn to move it
        self.drag_spawn_idx = None
        self.drag_start = None
        self.drag_moving = False
        self.pending_cycle = False

        # Coordinate display and tooltip
        self.coord_text = None
        self.coord_bg = None
        self.tooltip = None
        
        # MU Online style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#181c24', foreground='#e0e6f8', font=('Verdana', 10, 'bold'))
        style.configure('TLabel', background='#181c24', foreground='#e0e6f8', font=('Verdana', 10, 'bold'))
        style.configure('TFrame', background='#181c24')
        style.configure('TEntry', fieldbackground='#23293a', foreground='#e0e6f8', bordercolor='#bfa14a', font=('Verdana', 10, 'bold'))
        style.configure('TButton', background='#23293a', foreground='#e0e6f8', bordercolor='#bfa14a', font=('Verdana', 10, 'bold'), relief='raised')
        style.map('TButton', background=[('active', '#2e3a4e')], foreground=[('active', '#fff')])
        style.configure('TLabelframe', background='#181c24', foreground='#ffe066', bordercolor='#bfa14a', font=('Verdana', 10, 'bold'))
        style.configure('TLabelframe.Label', background='#181c24', foreground='#ffe066', font=('Verdana', 10, 'bold'))
        style.configure('TScrollbar', background='#23293a', troughcolor='#23293a', bordercolor='#bfa14a')
        # Listbox i canvas na ciemno
        self.root.option_add('*Listbox.background', '#23293a')
        self.root.option_add('*Listbox.foreground', '#e0e6f8')
        self.root.option_add('*Listbox.font', 'Verdana 10 bold')
        self.root.option_add('*Listbox.selectBackground', '#3a4a6d')
        self.root.option_add('*Listbox.selectForeground', '#ffe066')
        self.root.option_add('*Entry.background', '#23293a')
        self.root.option_add('*Entry.foreground', '#e0e6f8')
        self.root.option_add('*Entry.font', 'Verdana 10 bold')
        self.root.option_add('*TCombobox*Listbox.background', '#23293a')
        self.root.option_add('*TCombobox*Listbox.foreground', '#e0e6f8')
        self.root.option_add('*TCombobox*Listbox.font', 'Verdana 10 bold')
        # Spinbox styl
        self.root.option_add('*Spinbox.background', '#23293a')
        self.root.option_add('*Spinbox.foreground', '#e0e6f8')
        self.root.option_add('*Spinbox.font', 'Verdana 10 bold')
        self.root.option_add('*Spinbox.insertBackground', '#e0e6f8')
        style.configure('TSpinbox', fieldbackground='#23293a', foreground='#e0e6f8', font=('Verdana', 10, 'bold'))
        style.map('TCombobox', fieldbackground=[('readonly', '#23293a')], foreground=[('readonly', '#e0e6f8')])
        
        # Set minimum window size and maximize on start
        self.root.minsize(1200, 800)
        try:
            self.root.state('zoomed')  # Windows
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)  # Linux
            except tk.TclError:
                pass
        
        # Configure row and column weights for resizing - GŁÓWNA ZMIANA DLA RESPONSYWNOŚCI
        self.root.columnconfigure(0, weight=1)  # Główna kolumna rozciąga się
        self.root.rowconfigure(0, weight=1)     # Główny wiersz rozciąga się
        self.root.rowconfigure(1, weight=0)     # Status bar ma stałą wysokość
        
        # Add status bar at the bottom (Initialize early for use in load calls)
        self.create_status_bar()
        
        # Initialize dictionaries
        self.monsters = {}
        self.monster_stats = {}
        
        # Initialize image variables
        self.photo_image = None
        self.original_image = None
        self.original_width = 0
        self.original_height = 0
        self.scale = 1.0  # Default scale
        self.fit_to_window = True  # Refit the map on window resize (turned off by manual zoom)
        self.scaled_size = None
        self.missing_image_hint = None
        self.resize_job = None
        
        # Load monster data
        self.load_monster_data("Monster/Monster.txt")
        
        # Load monster stats
        self.load_monster_stats()
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # Configure main frame for resizing - LEPSZE PROPORCJE
        self.main_frame.columnconfigure(0, weight=2, minsize=350)  # Left panel (proporcja 2)
        self.main_frame.columnconfigure(1, weight=5, minsize=700)  # Right panel (proporcja 5)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Create menu
        self.create_menu()
        
        # Create main panels
        self.create_panels()
        
        # Bind closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.set_status("Select a map to start. Press F1 for keyboard shortcuts.")

    def set_program_icon(self):
        """Set the program icon if the icon file exists"""
        icon_path = "icon.ico"
        if not os.path.exists(icon_path):
            print("Icon file not found. Place 'icon.ico' in the program directory to set custom icon.")
            return
        try:
            self.root.iconbitmap(icon_path)
        except tk.TclError as e:
            # .ico files are only supported on Windows
            print(f"Warning: Could not set window icon: {str(e)}")
        if sys.platform == "win32":
            # Dla Windows, ustaw także ikonę w pasku zadań
            try:
                import ctypes
                myappid = 'shizoo.monsterspawneditor.1.0'  # arbitrary string
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception as e:
                print(f"Warning: Could not set taskbar icon: {str(e)}")

    def load_monster_data(self, filename):
        """Load basic monster data (ID, name, and type) from Monster.txt"""
        try:
            # Sprawdź czy katalog Monster istnieje, jeśli nie - utwórz go
            if not os.path.exists("Monster"):
                try:
                    os.makedirs("Monster")
                    self.status_var.set("Created Monster directory")
                    messagebox.showinfo("Directory Created", "Monster directory was created. Place your Monster.txt file in this directory.")
                    return
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to create Monster directory: {str(e)}")
                    return
            
            # Sprawdź czy plik Monster.txt istnieje
            if not os.path.exists(filename):
                self.status_var.set(f"File {filename} not found")
                messagebox.showinfo("File Not Found", f"{filename} not found. Create or copy this file to the Monster directory.")
                return
            
            with open(filename, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.strip() and not line.startswith('//'):
                        # Split by whitespace but preserve quoted strings
                        parts = []
                        in_quotes = False
                        current_part = []
                        
                        for char in line.strip():
                            if char == '"':
                                in_quotes = not in_quotes
                                if not in_quotes and current_part:
                                    parts.append(''.join(current_part))
                                    current_part = []
                            elif char.isspace() and not in_quotes:
                                if current_part:
                                    parts.append(''.join(current_part))
                                    current_part = []
                            else:
                                current_part.append(char)
                        
                        if current_part:
                            parts.append(''.join(current_part))
                        
                        if len(parts) >= 3 and parts[0].isdigit():
                            monster_id = int(parts[0])
                            # Extract full name (everything between quotes)
                            full_name = ""
                            match = re.search(r'"([^"]*)"', line)
                            if match:
                                full_name = match.group(1)
                            else:
                                full_name = parts[2].strip('"')
                            
                            # Default to monster type until we have more info
                            monster_type = 2  # Default to monster
                            
                            self.monsters[monster_id] = {
                                'name': full_name,
                                'type': monster_type
                            }
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load monster data: {str(e)}")
            # Inicjalizuj pustą listę, aby uniknąć błędów w innych miejscach
            if not self.monsters:
                self.monsters = {}

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Map", command=self.load_map_dialog, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_changes, accelerator="Ctrl+S")
        file_menu.add_command(label="Save All Modified Maps", command=self.save_all_changes, accelerator="Ctrl+Shift+S")
        file_menu.add_command(label="Revert Map to Saved", command=self.revert_map)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Alt+F4")
        
        # Create Edit menu separately and store references to menu items
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # Add Undo/Redo commands and store indices
        self.undo_index = 0  # First item (index 0)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z", state="disabled")
        
        self.redo_index = 1  # Second item (index 1)
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y", state="disabled")
        
        edit_menu.add_separator()  # This will be index 2
        edit_menu.add_command(label="Duplicate Selected Spawn", command=self.duplicate_selected_spawn, accelerator="Ctrl+D")
        edit_menu.add_command(label="Delete Selected Spawn", command=self.delete_selected_spawn, accelerator="Del")
        edit_menu.add_command(label="Clear Selection", command=self.clear_spawn_selection, accelerator="Esc")
        
        self.edit_menu = edit_menu  # Store reference to edit menu
        
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Opcja do pokazania/ukrycia mobów
        self.view_mobs_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Show Mobs", variable=self.view_mobs_var, command=self.toggle_mobs_visibility_menu)
        self.filter_map_var = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(label="Show Only Search Results on Map", variable=self.filter_map_var, command=self.display_spawns)
        
        # Opcje zmiany skali
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Fit to Window", command=self.reset_zoom, accelerator="Ctrl+0")
        view_menu.add_command(label="Actual Size (100%)", command=self.actual_size, accelerator="Ctrl+1")
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Instructions", command=self.show_instructions)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts, accelerator="F1")
        help_menu.add_command(label="About", command=self.show_about)
        
        # Bind keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self.load_map_dialog())
        self.root.bind("<Control-s>", lambda e: self.save_changes())
        self.root.bind("<Control-S>", lambda e: self.save_all_changes())  # Ctrl+Shift+S
        self.root.bind("<Delete>", lambda e: None if self.is_typing(e) else self.delete_selected_spawn())
        self.root.bind("<Control-d>", lambda e: None if self.is_typing(e) else self.duplicate_selected_spawn())
        self.root.bind("<Escape>", lambda e: self.clear_spawn_selection())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())  # Dla klawiatury amerykańskiej
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.reset_zoom())
        self.root.bind("<Control-1>", lambda e: self.actual_size())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<F1>", lambda e: self.show_shortcuts())

    @staticmethod
    def is_typing(event):
        """True if the key event comes from a text field (so Delete etc. edit the text instead)"""
        return isinstance(event.widget, (tk.Entry, tk.Spinbox))

    def create_panels(self):
        # Left panel
        self.left_panel = ttk.Frame(self.main_frame)
        self.left_panel.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # Configure left panel for resizing - POPRAWIONA RESPONSYWNOŚĆ
        self.left_panel.columnconfigure(0, weight=1)  # Kolumna rozciąga się na całą szerokość
        self.left_panel.rowconfigure(0, weight=1)  # Map selection
        self.left_panel.rowconfigure(1, weight=1)  # Monster list
        self.left_panel.rowconfigure(2, weight=2)  # Monster stats (większa proporcja)
        
        # Map selection
        self.create_map_selection()
        
        # Monster list
        self.create_monster_list()
        
        # Monster stats
        self.create_monster_stats()
        
        # Right panel (map view)
        self.right_panel = ttk.Frame(self.main_frame)
        self.right_panel.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # Configure right panel for resizing - POPRAWIONA RESPONSYWNOŚĆ
        self.right_panel.columnconfigure(0, weight=1)  # Kolumna rozciąga się
        self.right_panel.rowconfigure(0, weight=4)  # Map view (larger)
        self.right_panel.rowconfigure(1, weight=1)  # Spawn list
        
        self.create_map_view()
        
        # Spawn list panel
        self.create_spawn_list()

    def create_status_bar(self):
        """Create a status bar at the bottom of the window"""
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(2, 2, 2, 2))
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.S))
        
        # Configure status frame for resizing
        status_frame.columnconfigure(0, weight=3)  # Status message (proportion 3)
        status_frame.columnconfigure(1, weight=1)  # Coordinates (proportion 1)
        status_frame.columnconfigure(2, weight=1)  # Scale (proportion 1)
        status_frame.columnconfigure(3, weight=1)  # Modified indicator (proportion 1)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W)
        status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Add coordinates display in status bar
        self.coordinates_var = tk.StringVar(value="X: 0 Y: 0")
        coordinates_label = ttk.Label(status_frame, textvariable=self.coordinates_var, anchor=tk.E)
        coordinates_label.grid(row=0, column=1, sticky=(tk.E))
        
        # Add scale display in status bar
        self.scale_var = tk.StringVar(value="Scale: 100%")
        scale_label = ttk.Label(status_frame, textvariable=self.scale_var, anchor=tk.E)
        scale_label.grid(row=0, column=2, sticky=(tk.E), padx=(10, 0))
        
        # Add modified indicator
        self.modified_var = tk.StringVar(value="")
        modified_label = ttk.Label(status_frame, textvariable=self.modified_var, anchor=tk.E, foreground="red")
        modified_label.grid(row=0, column=3, sticky=(tk.E), padx=(10, 0))

    def create_map_selection(self):
        map_frame = ttk.LabelFrame(self.left_panel, text="Map Selection")
        map_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure map frame for resizing - POPRAWIONA RESPONSYWNOŚĆ
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(1, weight=1)

        # Search maps by name or number
        map_search_frame = ttk.Frame(map_frame)
        map_search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=(5, 0))
        map_search_frame.columnconfigure(1, weight=1)
        ttk.Label(map_search_frame, text="Search:").grid(row=0, column=0, sticky=tk.W)
        self.map_search_var = tk.StringVar()
        self.map_search_var.trace_add('write', lambda *args: self.refresh_map_list())
        ttk.Entry(map_search_frame, textvariable=self.map_search_var).grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Map list with scrollbar
        map_list_frame = ttk.Frame(map_frame)
        map_list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        map_list_frame.columnconfigure(0, weight=1)
        map_list_frame.rowconfigure(0, weight=1)
        
        self.map_listbox = tk.Listbox(map_list_frame, height=10, width=30, exportselection=False)
        self.map_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.map_listbox.bind('<<ListboxSelect>>', self.on_map_selected)
        
        # Add scrollbars
        map_y_scroll = ttk.Scrollbar(map_list_frame, orient="vertical", command=self.map_listbox.yview)
        map_y_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.map_listbox.configure(yscrollcommand=map_y_scroll.set)
        
        # Load maps
        self.load_available_maps()

    def create_monster_list(self):
        monster_frame = ttk.LabelFrame(self.left_panel, text="New Mob Selection")
        monster_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure monster frame for resizing - POPRAWIONA RESPONSYWNOŚĆ
        monster_frame.columnconfigure(0, weight=0)  # Etykieta nie rozciąga się
        monster_frame.columnconfigure(1, weight=1)  # Pole wyszukiwania rozciąga się
        monster_frame.rowconfigure(0, weight=0)     # Wyszukiwarka ma stałą wysokość
        monster_frame.rowconfigure(1, weight=1)     # Lista potworów rozciąga się
        monster_frame.rowconfigure(2, weight=0)     # Kontrolki ilości mają stałą wysokość
        
        # Search
        ttk.Label(monster_frame, text="Search:").grid(row=0, column=0, sticky=tk.W)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_monsters)
        search_entry = ttk.Entry(monster_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Monster list with scrollbar
        monster_list_frame = ttk.Frame(monster_frame)
        monster_list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        monster_list_frame.columnconfigure(0, weight=1)
        monster_list_frame.rowconfigure(0, weight=1)
        
        self.monster_listbox = tk.Listbox(monster_list_frame, height=10, width=25, exportselection=False)
        self.monster_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.monster_listbox.bind('<<ListboxSelect>>', self.on_monster_selected)
        
        # Add scrollbars - DODANO POZIOMY SCROLLBAR
        monster_y_scroll = ttk.Scrollbar(monster_list_frame, orient="vertical", command=self.monster_listbox.yview)
        monster_y_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        monster_x_scroll = ttk.Scrollbar(monster_list_frame, orient="horizontal", command=self.monster_listbox.xview)
        monster_x_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.monster_listbox.configure(yscrollcommand=monster_y_scroll.set, xscrollcommand=monster_x_scroll.set)
        
        # Quantity field for monsters (not used for NPCs)
        quantity_frame = ttk.Frame(monster_frame)
        quantity_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(quantity_frame, text="Quantity:").grid(row=0, column=0, sticky=tk.W)
        self.quantity_var = tk.IntVar(value=1)
        self.quantity_spinbox = tk.Spinbox(quantity_frame, from_=1, to=100, textvariable=self.quantity_var, width=5,
            background='#23293a', foreground='#e0e6f8', insertbackground='#e0e6f8', font=('Verdana', 10, 'bold'),
            highlightbackground='#bfa14a', highlightcolor='#ffe066', relief='flat', borderwidth=2)
        self.quantity_spinbox.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Default range
        ttk.Label(quantity_frame, text="Range:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.range_var = tk.IntVar(value=30)
        range_spinbox = tk.Spinbox(quantity_frame, from_=1, to=100, textvariable=self.range_var, width=5,
            background='#23293a', foreground='#e0e6f8', insertbackground='#e0e6f8', font=('Verdana', 10, 'bold'),
            highlightbackground='#bfa14a', highlightcolor='#ffe066', relief='flat', borderwidth=2)
        range_spinbox.grid(row=0, column=3, sticky=tk.W, padx=5)

        # Section of the MonsterSetBase file that new spawns are written to
        ttk.Label(quantity_frame, text="Add as:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.new_section_var = tk.StringVar(value="Auto")
        new_section_combo = ttk.Combobox(quantity_frame, textvariable=self.new_section_var, values=SECTION_CHOICES,
                                         state="readonly", width=18)
        new_section_combo.grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=5, pady=(5, 0))
        
        self.update_monster_list()

    def create_monster_stats(self):
        stats_frame = ttk.LabelFrame(self.left_panel, text="Selected Monster Stats")
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)  # Dodano N, S dla lepszego rozciągania
        
        # Poprawiona responsywność - frame ma lepszy podział
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.rowconfigure(0, weight=1)
        
        # Stats grid - create a frame to hold all the stats
        stats_container = ttk.Frame(stats_frame)
        stats_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))  # Dodano N, S dla lepszego rozciągania
        stats_container.columnconfigure(0, weight=1)
        stats_container.columnconfigure(1, weight=1)
        stats_container.columnconfigure(2, weight=1)
        
        self.stat_vars = {}
        self.stat_entries = {}
        
        # First row - basic info
        name_frame = ttk.Frame(stats_container)
        name_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        name_frame.columnconfigure(1, weight=1)  # Pole nazwy rozciąga się
        
        ttk.Label(name_frame, text="Name:").grid(row=0, column=0, sticky=tk.W)
        name_var = tk.StringVar()
        self.stat_vars["name"] = name_var
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=30)
        name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.stat_entries["name"] = name_entry
        
        # Dodaj pola do edycji koordynatów dla wybranego spawna
        spawn_coords_frame = ttk.LabelFrame(stats_container, text="Spawn Properties (selected spawn)")
        spawn_coords_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Konfiguracja responsywności dla ramki koordynatów
        spawn_coords_frame.columnconfigure(0, weight=0)  # Etykieta
        spawn_coords_frame.columnconfigure(1, weight=1)  # Pole X / Qty
        spawn_coords_frame.columnconfigure(2, weight=0)  # Etykieta
        spawn_coords_frame.columnconfigure(3, weight=1)  # Pole Y / Range
        
        # Zmienne dla koordynatów X, Y
        self.spawn_x_var = tk.IntVar(value=0)
        self.spawn_y_var = tk.IntVar(value=0)
        self.spawn_end_x_var = tk.IntVar(value=0)
        self.spawn_end_y_var = tk.IntVar(value=0)
        self.spawn_qty_var = tk.IntVar(value=1)
        self.spawn_range_var = tk.IntVar(value=0)
        self.spawn_dir_var = tk.IntVar(value=-1)
        self.spawn_section_var = tk.StringVar()

        spinbox_style = dict(background='#23293a', foreground='#e0e6f8', insertbackground='#e0e6f8', font=('Verdana', 10, 'bold'),
            highlightbackground='#bfa14a', highlightcolor='#ffe066', relief='flat', borderwidth=2)
        
        # Koordynaty punktu początkowego
        ttk.Label(spawn_coords_frame, text="Start X:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        spawn_x_entry = ttk.Entry(spawn_coords_frame, textvariable=self.spawn_x_var, width=5)
        spawn_x_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(spawn_coords_frame, text="Start Y:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        spawn_y_entry = ttk.Entry(spawn_coords_frame, textvariable=self.spawn_y_var, width=5)
        spawn_y_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Koordynaty punktu końcowego (dla obszarów)
        ttk.Label(spawn_coords_frame, text="End X:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        spawn_end_x_entry = ttk.Entry(spawn_coords_frame, textvariable=self.spawn_end_x_var, width=5)
        spawn_end_x_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(spawn_coords_frame, text="End Y:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        spawn_end_y_entry = ttk.Entry(spawn_coords_frame, textvariable=self.spawn_end_y_var, width=5)
        spawn_end_y_entry.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)

        # Ilość i Zasięg
        ttk.Label(spawn_coords_frame, text="Quantity:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        spawn_qty_entry = tk.Spinbox(spawn_coords_frame, from_=1, to=999, textvariable=self.spawn_qty_var, width=5, **spinbox_style)
        spawn_qty_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(spawn_coords_frame, text="Range:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        spawn_range_entry = tk.Spinbox(spawn_coords_frame, from_=0, to=255, textvariable=self.spawn_range_var, width=5, **spinbox_style)
        spawn_range_entry.grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Kierunek i sekcja pliku
        ttk.Label(spawn_coords_frame, text="Direction:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        spawn_dir_entry = tk.Spinbox(spawn_coords_frame, from_=-1, to=8, textvariable=self.spawn_dir_var, width=5, **spinbox_style)
        spawn_dir_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(spawn_coords_frame, text="Section:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        spawn_section_combo = ttk.Combobox(spawn_coords_frame, textvariable=self.spawn_section_var,
                                           values=SECTION_CHOICES[1:], state="readonly", width=16)
        spawn_section_combo.grid(row=3, column=3, sticky=tk.W, padx=5, pady=2)
        spawn_section_combo.bind("<<ComboboxSelected>>", lambda e: self.update_spawn_props_state())

        # End position and quantity only exist for area sections
        self.spawn_area_widgets = [spawn_end_x_entry, spawn_end_y_entry, spawn_qty_entry]

        # Enter in any field applies the changes
        for widget in (spawn_x_entry, spawn_y_entry, spawn_end_x_entry, spawn_end_y_entry,
                       spawn_qty_entry, spawn_range_entry, spawn_dir_entry):
            widget.bind("<Return>", lambda e: self.update_selected_spawn())

        # Przyciski
        spawn_buttons = ttk.Frame(spawn_coords_frame)
        spawn_buttons.grid(row=4, column=0, columnspan=4, sticky=tk.E, padx=5, pady=5)
        ttk.Button(spawn_buttons, text="Update Spawn", command=self.update_selected_spawn).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(spawn_buttons, text="Duplicate", command=self.duplicate_selected_spawn).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(spawn_buttons, text="Delete", command=self.delete_selected_spawn).grid(row=0, column=2)
        
        # Ukryj pola na początku (będą widoczne tylko po wybraniu spawna)
        spawn_coords_frame.grid_remove()
        self.spawn_coords_frame = spawn_coords_frame
        
        # Create 3-column grid for stats with scrollable area
        row = 2  # Zmienione z 1 na 2, żeby uwzględnić ramkę koordynatów
        
        # Utwórz ramkę z przewijaniem dla statystyk - NOWA FUNKCJONALNOŚĆ DLA LEPSZEJ RESPONSYWNOŚCI
        stats_scroll_frame = ttk.Frame(stats_container)
        stats_scroll_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        stats_scroll_frame.columnconfigure(0, weight=1)
        stats_scroll_frame.rowconfigure(0, weight=1)
        
        # Canvas do przewijania
        stats_canvas = tk.Canvas(stats_scroll_frame, borderwidth=0, highlightthickness=0, background='#181c24')
        stats_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        stats_scrollbar = ttk.Scrollbar(stats_scroll_frame, orient="vertical", command=stats_canvas.yview)
        stats_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        stats_canvas.configure(yscrollcommand=stats_scrollbar.set)
        
        # Wewnętrzna ramka dla statystyk
        stats_inner_frame = ttk.Frame(stats_canvas)
        stats_inner_frame.columnconfigure(0, weight=1)
        stats_inner_frame.columnconfigure(1, weight=1)
        stats_inner_frame.columnconfigure(2, weight=1)
        
        # Dodaj ramkę do canvas
        stats_canvas.create_window((0, 0), window=stats_inner_frame, anchor="nw", tags="stats_inner_frame")
        
        # Konfiguruj canvas do przewijania
        def _configure_stats_canvas(event):
            # Ustaw scrollregion na podstawie rozmiaru wewnętrznej ramki
            stats_canvas.configure(scrollregion=stats_canvas.bbox("all"))
            # Ustaw szerokość wewnętrznej ramki na szerokość canvas
            width = event.width
            stats_canvas.itemconfig("stats_inner_frame", width=width)
        
        stats_canvas.bind("<Configure>", _configure_stats_canvas)
        stats_inner_frame.bind("<Configure>", lambda e: stats_canvas.configure(scrollregion=stats_canvas.bbox("all")))
        
        # Definicje statystyk
        stats = [
            # First column
            [("ID", "id", 5), ("Rate", "attackrate", 5), ("Level", "level", 5), 
             ("HP", "hp", 5), ("MP", "mp", 5), ("MinDmg", "mindmg", 5), 
             ("MaxDmg", "maxdmg", 5), ("Def", "defense", 5), ("MagDef", "magdefense", 5)],
            # Second column
            [("Attack", "attack", 5), ("Success", "success", 5), ("Move", "moverange", 5),
             ("A.Type", "attacktype", 5), ("A.Range", "attackrange", 5), ("V.Range", "viewrange", 5),
             ("MovSP", "movespeed", 5), ("A.Speed", "attackspeed", 5), ("RegTime", "regtime", 5)],
            # Third column
            [("ItemR", "itemrate", 5), ("MoneyR", "moneyrate", 5), ("MaxiS", "maxistone", 5),
             ("Attrb", "attribute", 5), ("RWind", "resistwind", 5), ("RPos", "resistpoison", 5),
             ("RIce", "resistice", 5), ("RWtr", "resistwater", 5), ("RFire", "resistfire", 5)]
        ]
        
        # Dodawanie statystyk do ramki z przewijaniem
        for col, col_stats in enumerate(stats):
            col_frame = ttk.Frame(stats_inner_frame)
            col_frame.grid(row=0, column=col, sticky=(tk.N, tk.W), padx=5, pady=5)
            
            for i, (label, key, width) in enumerate(col_stats):
                ttk.Label(col_frame, text=label).grid(row=i, column=0, sticky=tk.W)
                var = tk.StringVar()
                self.stat_vars[key] = var
                
                # Create spinbox instead of readonly entry
                spinbox = tk.Spinbox(col_frame, from_=0, to=9999, textvariable=var, width=width,
                    background='#23293a', foreground='#e0e6f8', insertbackground='#e0e6f8', font=('Verdana', 10, 'bold'),
                    highlightbackground='#bfa14a', highlightcolor='#ffe066', relief='flat', borderwidth=2)
                spinbox.grid(row=i, column=1, sticky=tk.W, padx=2)
                self.stat_entries[key] = spinbox
        
        # Element stats (in another row below)
        element_frame = ttk.Frame(stats_inner_frame)
        element_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        element_stats = [
            ("Element", "element", 5), ("MinElem", "minelement", 5), ("MaxElem", "maxelement", 5), 
            ("ElemDef", "elementdef", 5)
        ]
        
        for i, (label, key, width) in enumerate(element_stats):
            ttk.Label(element_frame, text=label).grid(row=0, column=i*2, sticky=tk.W)
            var = tk.StringVar()
            self.stat_vars[key] = var
            spinbox = tk.Spinbox(element_frame, from_=0, to=9999, textvariable=var, width=width,
                background='#23293a', foreground='#e0e6f8', insertbackground='#e0e6f8', font=('Verdana', 10, 'bold'),
                highlightbackground='#bfa14a', highlightcolor='#ffe066', relief='flat', borderwidth=2)
            spinbox.grid(row=0, column=i*2+1, sticky=tk.W, padx=2)
            self.stat_entries[key] = spinbox
        
        # Update button
        update_button = ttk.Button(stats_inner_frame, text="Update Mob Stats", command=self.update_monster_stats)
        update_button.grid(row=2, column=0, columnspan=3, sticky=(tk.E), pady=5)
        
        # Bottom controls section (Direction and Mob Type side by side)
        controls_frame = ttk.Frame(stats_inner_frame)
        controls_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=1)
        
        # Direction controls
        direction_frame = ttk.LabelFrame(controls_frame, text="Direction (new spawns)")
        direction_frame.grid(row=0, column=0, sticky=(tk.W, tk.N, tk.E), padx=(0, 5), pady=5)
        
        self.direction_var = tk.IntVar(value=-1)
        
        # Direction layout with numbers visible (6,5,4,3,2,1,8,7, środek -1)
        dir_frame = ttk.Frame(direction_frame)
        dir_frame.grid(row=0, column=0, padx=10, pady=10)
        
        # Direction grid with visible numbers
        directions = [
            ['7', '6', '5'],
            ['8', '-1', '4'],
            ['1', '2', '3']
        ]
        
        for row_idx, row_values in enumerate(directions):
            for col_idx, value in enumerate(row_values):
                val = int(value) if value != '-1' else -1
                rb = tk.Radiobutton(dir_frame, text=value, variable=self.direction_var, value=val, 
                                   command=self.update_direction_label, width=3, indicatoron=0,
                                   background='#23293a', foreground='#e0e6f8', selectcolor='#3a4a6d',
                                   font=('Verdana', 10, 'bold'))
                rb.grid(row=row_idx, column=col_idx, padx=2, pady=2)
        
        # Label pokazujący wybrany kierunek
        self.direction_label_var = tk.StringVar(value="Selected direction: -1")
        direction_label = ttk.Label(direction_frame, textvariable=self.direction_label_var, font=("Arial", 10, "bold"))
        direction_label.grid(row=1, column=0, sticky=tk.W, padx=10, pady=(0,5))
        self.update_direction_label()
        
        # Monster type (Attribute column of Monster.txt), used by "Update Mob Stats"
        mob_type_frame = ttk.LabelFrame(controls_frame, text="Monster Type")
        mob_type_frame.grid(row=0, column=1, sticky=(tk.W, tk.N, tk.E), padx=(5, 0), pady=5)
        
        self.mob_type_var = tk.IntVar(value=2)  # Default to Monster
        
        for i, (value, text) in enumerate([(0, "NPC"), (1, "Trap"), (2, "Monster")]):
            rb = tk.Radiobutton(mob_type_frame, text=f"({value}) {text}", variable=self.mob_type_var, value=value,
                                background='#181c24', foreground='#e0e6f8', selectcolor='#23293a',
                                activebackground='#2e3a4e', activeforeground='#ffffff', font=('Verdana', 10, 'bold'))
            rb.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)

    def create_map_view(self):
        map_frame = ttk.LabelFrame(self.right_panel, text="Map View")
        map_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure map frame for resizing - POPRAWIONA RESPONSYWNOŚĆ
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(0, weight=1)
        map_frame.rowconfigure(1, weight=0)  # Scrollbar horyzontalny ma stałą wysokość
        map_frame.rowconfigure(2, weight=0)  # Legenda
        
        # Canvas for map with frame for proper resizing
        canvas_frame = ttk.Frame(map_frame)
        canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        # Canvas for map - DODANO MIN SIZE DLA POPRAWY RESPONSYWNOŚCI
        self.map_canvas = tk.Canvas(canvas_frame, width=800, height=600, bg="light gray", highlightthickness=0)
        self.map_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbars
        x_scroll = ttk.Scrollbar(map_frame, orient="horizontal", command=self.map_canvas.xview)
        x_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        y_scroll = ttk.Scrollbar(map_frame, orient="vertical", command=self.map_canvas.yview)
        y_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.map_canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        
        # Legend: colour of each MonsterSetBase section
        legend = ttk.Frame(map_frame)
        legend.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=2, pady=(4, 0))
        for col, (section, (name, color)) in enumerate(SECTIONS.items()):
            tk.Label(legend, text="", bg=color, width=2).grid(row=0, column=col * 2, padx=(10 if col else 0, 3))
            ttk.Label(legend, text=f"{section} {name}").grid(row=0, column=col * 2 + 1, sticky=tk.W)
        ttk.Label(legend, foreground="#8f9bb8", font=('Verdana', 8),
                  text="Click: add / select  |  Drag empty area: area spawn  |  Drag spawn: move  |  "
                       "Right-click: more  |  Ctrl+Wheel: zoom  |  Arrows: nudge"
                  ).grid(row=1, column=0, columnspan=len(SECTIONS) * 2, sticky=tk.W, pady=(2, 0))

        # Bind events
        self.map_canvas.bind("<Motion>", self.on_mouse_move)
        self.map_canvas.bind("<Leave>", self.remove_coord_overlay)
        self.map_canvas.bind("<Button-1>", self.on_mouse_down)
        self.map_canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.map_canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.map_canvas.bind("<Button-3>", self.on_right_click)
        
        # Middle mouse button pans, the wheel scrolls (Ctrl+wheel zooms)
        self.map_canvas.bind("<ButtonPress-2>", lambda e: self.map_canvas.scan_mark(e.x, e.y))
        self.map_canvas.bind("<B2-Motion>", lambda e: self.map_canvas.scan_dragto(e.x, e.y, gain=1))
        self.map_canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows / macOS
        self.map_canvas.bind("<Button-4>", self.on_mouse_wheel)    # Linux: wheel up
        self.map_canvas.bind("<Button-5>", self.on_mouse_wheel)    # Linux: wheel down

        # Arrow keys nudge the selected spawn (map X runs down the image, map Y to the right)
        for key, (dx, dy) in {"<Up>": (-1, 0), "<Down>": (1, 0), "<Left>": (0, -1), "<Right>": (0, 1)}.items():
            self.map_canvas.bind(key, lambda e, dx=dx, dy=dy: self.nudge_selected_spawn(dx, dy))

        # Hover tooltips (tag bindings also apply to dots drawn later)
        self.map_canvas.tag_bind("dot", "<Enter>", self.on_spawn_hover)
        self.map_canvas.tag_bind("dot", "<Leave>", self.hide_spawn_tooltip)

        # Refit the map when the canvas changes size
        self.map_canvas.bind("<Configure>", self.on_canvas_resize)

    def create_spawn_list(self):
        """Create a panel to display and manage current spawns"""
        spawn_frame = ttk.LabelFrame(self.right_panel, text="Mobs on Selected Map")
        spawn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure spawn frame for resizing - POPRAWIONA RESPONSYWNOŚĆ
        spawn_frame.columnconfigure(0, weight=1)
        spawn_frame.rowconfigure(0, weight=0)  # Search ma stałą wysokość
        spawn_frame.rowconfigure(1, weight=0)  # Opcje mają stałą wysokość
        spawn_frame.rowconfigure(2, weight=1)  # Lista spawnów rozciąga się
        spawn_frame.rowconfigure(3, weight=0)  # Przyciski mają stałą wysokość
        
        # WYSZUKIWARKA
        search_frame = ttk.Frame(spawn_frame)
        search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=(2, 0))
        search_frame.columnconfigure(1, weight=1)  # Pole wyszukiwania rozciąga się
        
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, sticky=tk.W)
        self.spawn_search_var = tk.StringVar()
        self.spawn_search_var.trace_add('write', self.on_spawn_search_changed)
        search_entry = ttk.Entry(search_frame, textvariable=self.spawn_search_var, width=30)
        search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        ttk.Button(search_frame, text="Clear", width=6,
                   command=lambda: self.spawn_search_var.set("")).grid(row=0, column=2, padx=(5, 0))
        ttk.Label(search_frame, foreground="#8f9bb8", font=('Verdana', 8),
                  text="name, ID, npc / trap / monster or X,Y").grid(row=1, column=1, sticky=tk.W)
        
        # Options: hide mobs, filter map by search, summary
        options_frame = ttk.Frame(spawn_frame)
        options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=2)
        options_frame.columnconfigure(2, weight=1)
        self.hide_mobs_var = tk.BooleanVar(value=False)
        hide_mobs_cb = ttk.Checkbutton(options_frame, text="Hide Mobs", variable=self.hide_mobs_var,
                                      command=self.toggle_mobs_visibility)
        hide_mobs_cb.grid(row=0, column=0, sticky=tk.W)
        filter_map_cb = ttk.Checkbutton(options_frame, text="Show only search results on map",
                                        variable=self.filter_map_var, command=self.display_spawns)
        filter_map_cb.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        self.spawn_summary_var = tk.StringVar(value="")
        ttk.Label(options_frame, textvariable=self.spawn_summary_var, anchor=tk.E).grid(row=0, column=2, sticky=(tk.E))
        
        # Create spawn list with scrollbar
        spawn_list_frame = ttk.Frame(spawn_frame)
        spawn_list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure spawn list frame for resizing
        spawn_list_frame.columnconfigure(0, weight=1)
        spawn_list_frame.rowconfigure(0, weight=1)
        
        # Spawn list
        self.spawn_listbox = tk.Listbox(spawn_list_frame, height=10, width=50, exportselection=False)
        self.spawn_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.spawn_listbox.bind('<<ListboxSelect>>', self.on_spawn_selected)
        
        # Scrollbar for spawn list - DODANO POZIOMY SCROLLBAR
        spawn_y_scrollbar = ttk.Scrollbar(spawn_list_frame, orient="vertical", command=self.spawn_listbox.yview)
        spawn_y_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        spawn_x_scrollbar = ttk.Scrollbar(spawn_list_frame, orient="horizontal", command=self.spawn_listbox.xview)
        spawn_x_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.spawn_listbox.configure(yscrollcommand=spawn_y_scrollbar.set, xscrollcommand=spawn_x_scrollbar.set)
        
        # Button frame
        button_frame = ttk.Frame(spawn_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.E), padx=5, pady=5)
        
        duplicate_button = ttk.Button(button_frame, text="Duplicate", command=self.duplicate_selected_spawn)
        duplicate_button.grid(row=0, column=0, sticky=(tk.E), padx=5)

        # Remove button
        delete_button = ttk.Button(button_frame, text="Remove", command=self.delete_selected_spawn)
        delete_button.grid(row=0, column=1, sticky=(tk.E), padx=5)

    def load_monster_stats(self):
        """Load detailed monster stats and determine correct monster types"""
        try:
            with open("Monster/Monster.txt", 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.strip() and not line.startswith('//'):
                        # Split by whitespace but preserve quoted strings
                        parts = []
                        in_quotes = False
                        current_part = []
                        
                        for char in line.strip():
                            if char == '"':
                                in_quotes = not in_quotes
                                if not in_quotes and current_part:
                                    parts.append(''.join(current_part))
                                    current_part = []
                            elif char.isspace() and not in_quotes:
                                if current_part:
                                    parts.append(''.join(current_part))
                                    current_part = []
                            else:
                                current_part.append(char)
                        
                        if current_part:
                            parts.append(''.join(current_part))
                        
                        if len(parts) >= 17 and parts[0].isdigit():  # Make sure we have enough columns to read attribute
                            try:
                                monster_id = int(parts[0])
                                
                                # Extract full name (everything between quotes)
                                full_name = ""
                                match = re.search(r'"([^"]*)"', line)
                                if match:
                                    full_name = match.group(1)
                                else:
                                    full_name = parts[2].strip('"')
                                
                                # Get attack type (column 13) and attribute (column 19)
                                attack_type = -1
                                attribute = -1
                                
                                if len(parts) > 13 and parts[13].isdigit():
                                    attack_type = int(parts[13])
                                
                                if len(parts) > 19 and parts[19].isdigit():  # Changed from 17 to 19
                                    attribute = int(parts[19])
                                    # Limit attribute to valid values (0, 1, 2)
                                    if attribute not in [0, 1, 2]:
                                        print(f"Warning: Invalid attribute value {attribute} for monster {monster_id}, setting to 2 (monster)")
                                        attribute = 2  # Default to monster type if invalid
                                
                                # Debug output for all monsters
                                # print(f"Processing monster: ID={monster_id}, Name={full_name}")
                                # print(f"Parts: {parts}")
                                # print(f"Number of parts: {len(parts)}")
                                # print(f"Attack type: {attack_type}, Attribute: {attribute}")
                                
                                # Use attribute to determine monster type:
                                # 0 = NPC, 1 = Trap, 2 = Monster
                                monster_type = attribute  # Use attribute value directly as monster type
                                
                                # Store all monster data in stats
                                try:
                                    level = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
                                    hp = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
                                    mp = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0
                                    mindmg = int(parts[6]) if len(parts) > 6 and parts[6].isdigit() else 0
                                    maxdmg = int(parts[7]) if len(parts) > 7 and parts[7].isdigit() else 0
                                    defense = int(parts[8]) if len(parts) > 8 and parts[8].isdigit() else 0
                                    attackrate = int(parts[10]) if len(parts) > 10 and parts[10].isdigit() else 0
                                    moverange = int(parts[12]) if len(parts) > 12 and parts[12].isdigit() else 0
                                    viewrange = int(parts[14]) if len(parts) > 14 and parts[14].isdigit() else 0
                                except (IndexError, ValueError):
                                    level = hp = mp = mindmg = maxdmg = defense = attackrate = moverange = viewrange = 0

                                self.monster_stats[monster_id] = {
                                    'id': monster_id,
                                    'name': full_name,
                                    'type': monster_type,
                                    'level': level,
                                    'hp': hp,
                                    'mp': mp,
                                    'mindmg': mindmg,
                                    'maxdmg': maxdmg,
                                    'defense': defense,
                                    'attackrate': attackrate,
                                    'moverange': moverange,
                                    'attacktype': attack_type,
                                    'viewrange': viewrange,
                                    'attribute': attribute  # Store attribute value
                                }
                                
                                # Update the monster type in the monsters dictionary
                                if monster_id in self.monsters:
                                    self.monsters[monster_id]['type'] = monster_type
                                    
                            except (IndexError, ValueError) as e:
                                print(f"Warning: Could not parse monster stats for line: {line.strip()}")
                                continue
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load monster stats: {str(e)}")

    def load_available_maps(self):
        self.map_files = []
        
        # Sprawdź czy katalog istnieje, jeśli nie - utwórz go
        if not os.path.exists("MonsterSetBase"):
            try:
                os.makedirs("MonsterSetBase")
                self.set_status("Created MonsterSetBase directory")
                messagebox.showinfo("Directory Created", "MonsterSetBase directory was created. Place your map files in this directory.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create MonsterSetBase directory: {str(e)}")
            self.refresh_map_list()
            return
        
        # Wczytaj pliki map
        try:
            self.map_files = [f for f in sorted(os.listdir("MonsterSetBase"))
                              if f.endswith(".txt") and not f.startswith("Event")]
            if not self.map_files:
                self.set_status("No map files found in MonsterSetBase directory")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load maps: {str(e)}")
        self.refresh_map_list()

    def refresh_map_list(self):
        """Fill the map list, applying the search filter and marking maps with unsaved changes with *"""
        search_text = self.map_search_var.get().lower().strip() if hasattr(self, 'map_search_var') else ""
        top = self.map_listbox.yview()[0]
        self.map_listbox.delete(0, tk.END)
        self.map_list_rows = []
        for map_file in self.map_files:
            if search_text and search_text not in map_file.lower():
                continue
            label = map_file + ("  *" if map_file in self.modified_maps else "")
            self.map_listbox.insert(tk.END, label)
            self.map_list_rows.append(map_file)
            if map_file == self.selected_map_file:
                self.map_listbox.selection_set(len(self.map_list_rows) - 1)
        self.map_listbox.yview_moveto(top)

    def load_map_dialog(self):
        # Open file dialog to select map file
        file_path = filedialog.askopenfilename(
            title="Select MonsterSetBase file",
            initialdir="MonsterSetBase",
            filetypes=[("Text Files", "*.txt")]
        )
        if not file_path:
            return
        # Maps are always read from and saved to the MonsterSetBase folder
        folder = os.path.normcase(os.path.abspath(os.path.dirname(file_path)))
        if folder != os.path.normcase(os.path.abspath("MonsterSetBase")):
            messagebox.showwarning("Warning", "Please choose a file from the editor's MonsterSetBase folder.")
            return
        self.open_map(os.path.basename(file_path))

    def read_spawn_file(self, map_file):
        """Parse a MonsterSetBase file. Returns (spawns, number of lines that could not be read)"""
        spawns = []
        skipped = 0
        section = None
        with open(os.path.join("MonsterSetBase", map_file), 'r', errors='replace') as f:
            for raw_line in f:
                # Drop comments, also ones glued to the last value (e.g. "3//Guard")
                line = raw_line.split('//', 1)[0].strip()
                if not line:
                    continue
                parts = line.split()
                # Section markers: a single number on its own line
                if len(parts) == 1 and parts[0].isdigit():
                    section = int(parts[0])
                    continue
                if line.lower() == "end":
                    section = None
                    continue
                try:
                    values = [int(p) for p in parts]
                except ValueError:
                    values = []
                spawn_section = section
                if spawn_section is None and values:
                    # Legacy file without section markers
                    if len(values) >= 9:
                        spawn_section = 1
                    else:
                        spawn_section = 0 if self.get_monster_type(values[0]) == 0 else 2
                needed = 9 if spawn_section in AREA_SECTIONS else 6
                if len(values) < needed:
                    print(f"Warning: Skipping malformed line: {raw_line.strip()}")
                    skipped += 1
                    continue
                if spawn_section in AREA_SECTIONS:
                    x, y, end_x, end_y, direction, quantity = values[3:9]
                else:
                    x, y, direction = values[3], values[4], values[5]
                    end_x, end_y, quantity = x, y, 1
                spawns.append({
                    'monster_id': values[0],
                    'map_number': values[1],
                    'range': values[2],
                    'x': x,
                    'y': y,
                    'end_x': end_x,
                    'end_y': end_y,
                    'direction': direction,
                    'quantity': quantity,
                    'section': spawn_section
                })
        return spawns, skipped

    def open_map(self, map_file, reload_from_disk=False):
        """Switch to map_file, using the copy in memory unless reload_from_disk. Returns True on success."""
        if map_file == self.selected_map_file and not reload_from_disk:
            return True
        skipped = 0
        if map_file in self.map_spawns and not reload_from_disk:
            spawns = copy.deepcopy(self.map_spawns[map_file])
        else:
            try:
                spawns, skipped = self.read_spawn_file(map_file)
            except Exception as e:
                traceback.print_exc()
                messagebox.showerror("Error", f"Failed to load map: {str(e)}")
                self.refresh_map_list()  # Restore the highlight of the current map
                return False

        # Keep the current map's spawns and undo history in memory
        if self.selected_map_file:
            self.save_map_to_memory(self.selected_map_file)
            self.map_history[self.selected_map_file] = (self.undo_stack, self.redo_stack)

        self.selected_map_file = map_file
        self.spawns = spawns
        self.map_spawns[map_file] = copy.deepcopy(spawns)
        if reload_from_disk:
            self.map_history.pop(map_file, None)
        self.undo_stack, self.redo_stack = self.map_history.get(map_file, ([], []))
        self.update_undo_redo_states()
        self.clear_spawn_selection(redraw=False)
        
        map_name = self.map_name_from_file(map_file)
        self.display_map_image(self.find_map_image(map_name), map_name)
        self.update_spawn_list()
        self.refresh_map_list()
        self.update_modified_indicator()
                        
        if map_file in self.modified_maps:
            self.set_status(f"Loaded modified map: {map_file} ({len(spawns)} entries)")
        else:
            self.set_status(f"Loaded map: {map_file} ({len(spawns)} entries)")
        if skipped:
            messagebox.showwarning(
                "Unreadable Lines",
                f"{skipped} line(s) in {map_file} could not be read (see the console for details).\n"
                "They will be left out if you save this map.")
        return True
            
    def revert_map(self):
        """Discard unsaved changes of the current map and reload it from disk"""
        map_file = self.selected_map_file
        if not map_file:
            messagebox.showwarning("Warning", "Please select a map first")
            return
        if map_file in self.modified_maps and not messagebox.askyesno(
                "Revert Map", f"Discard all unsaved changes to {map_file}?", icon="warning"):
            return
        if self.open_map(map_file, reload_from_disk=True):
            self.modified_maps.discard(map_file)
            self.update_modified_indicator()
            self.refresh_map_list()
            self.set_status(f"Reverted {map_file} to the saved file")
            
    def update_modified_indicator(self):
        """Update the modified indicator in status bar"""
        if self.selected_map_file in self.modified_maps:
            self.modified_var.set("Modified*")
        else:
            self.modified_var.set("")

    def mark_modified(self):
        """Flag the current map as having unsaved changes"""
        if not self.selected_map_file:
            return
        was_modified = self.selected_map_file in self.modified_maps
        self.modified_maps.add(self.selected_map_file)
        self.update_modified_indicator()
        if not was_modified:
            self.refresh_map_list()

    def set_status(self, message):
        self.status_var.set(message)

    @staticmethod
    def map_name_from_file(map_file):
        """'056 - Swamp of Calmness.txt' -> 'Swamp of Calmness'"""
        name = os.path.splitext(map_file)[0]
        if " - " in name:
            name = name.split(" - ", 1)[1]
        return name.strip()

    def get_map_number(self, map_file):
        """Map number from the file name prefix ('007 - Atlans.txt' -> 7)"""
        try:
            return int(map_file.split(" - ")[0])
        except ValueError:
            # Fall back to the map number used by the spawns already on this map
            return self.spawns[0]['map_number'] if self.spawns else 0

    def get_monster_type(self, monster_id):
        """0 = NPC, 1 = Trap, 2 = Monster (Attribute column of Monster.txt)"""
        return self.monsters.get(monster_id, {}).get('type', 2)

    def get_monster_name(self, monster_id):
        return self.monsters.get(monster_id, {}).get('name', "Unknown")

    @staticmethod
    def section_name(section):
        return SECTIONS.get(section, (f"Section {section}", "white"))[0]

    @staticmethod
    def section_color(section):
        return SECTIONS.get(section, ("", "white"))[1]

    def section_label(self, section):
        return f"{section} - {self.section_name(section)}"

    @staticmethod
    def parse_section_choice(choice, default):
        """'2 - Single spots' -> 2, anything else (e.g. 'Auto') -> default"""
        number = choice.split(" ", 1)[0] if choice else ""
        return int(number) if number.isdigit() else default

    def find_map_image(self, map_name):
        """Find the image for a map in the Images folder (ignoring case and spaces vs underscores)"""
        # Sprawdź czy katalog Images istnieje, jeśli nie - utwórz go
        if not os.path.exists("Images"):
            try:
                os.makedirs("Images")
                self.set_status("Created Images directory")
                messagebox.showinfo("Directory Created", "Images directory was created. Place your map images in this directory.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create Images directory: {str(e)}")
            return None
        
        # Maps whose image has a different name
        map_exceptions = {
            'swamp of calmness': 'Swamp_of_Peace.png',
            'barracks': 'Barracks_of_Balgass.png',
        }
        mapped = map_exceptions.get(map_name.lower())
        if mapped and os.path.exists(os.path.join("Images", mapped)):
            return os.path.join("Images", mapped)
        
        base = map_name.strip().replace(" ", "_").lower()
        try:
            files = [f for f in os.listdir("Images") if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))]
        except OSError:
            return None
        # Exact name first, then a file that contains the map name
        for f in files:
            if os.path.splitext(f)[0].replace(" ", "_").lower() == base:
                return os.path.join("Images", f)
        for f in files:
            if base in f.replace(" ", "_").lower():
                return os.path.join("Images", f)
        return None

    def display_map_image(self, image_path, map_name=""):
        """Load the map image (or a placeholder grid if it is missing) and fit it into the canvas"""
        image = None
        self.missing_image_hint = None
        if image_path and os.path.exists(image_path):
            try:
                image = Image.open(image_path)
                image.load()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load map image: {str(e)}")
                image = None
        if image is None:
            expected = f"Images/{map_name.replace(' ', '_')}.png" if map_name else "Images/<Map_Name>.png"
            self.missing_image_hint = f"Map image not found\nAdd {expected} to see the map"
            self.set_status(f"Map image not found - add {expected}")
            image = self.create_placeholder_image()
            
        self.original_image = image
        self.original_width, self.original_height = image.size
        self.scaled_size = None
        self.fit_map_to_window()
        
    @staticmethod
    def create_placeholder_image(size=768):
        """Dark grid used when a map has no image (a line every 32 game cells)"""
        image = Image.new("RGB", (size, size), "#222222")
        draw = ImageDraw.Draw(image)
        for i in range(1, 8):
            pos = int(i * size / 8)
            draw.line([(pos, 0), (pos, size)], fill="#333a4a")
            draw.line([(0, pos), (size, pos)], fill="#333a4a")
        return image
        
    def fit_map_to_window(self):
        """Scale the map so it fits in the visible canvas"""
        if self.original_image is None:
            return
        canvas_width = self.map_canvas.winfo_width()
        canvas_height = self.map_canvas.winfo_height()
        # Jeśli canvas nie ma jeszcze właściwego rozmiaru, użyj domyślnych wartości
        if canvas_width <= 1:
            canvas_width = 800
        if canvas_height <= 1:
            canvas_height = 600
        self.scale = min(canvas_width / self.original_width, canvas_height / self.original_height)
        self.fit_to_window = True
        self.render_map()

    def render_map(self):
        """Draw the map image at the current scale and redraw the spawns on top"""
        if self.original_image is None:
            return
        width = max(1, int(self.original_width * self.scale))
        height = max(1, int(self.original_height * self.scale))
        # Resizing is slow, so only do it when the size actually changed
        if self.scaled_size != (width, height):
            if (width, height) == self.original_image.size:
                image = self.original_image
            else:
                image = self.original_image.resize((width, height), LANCZOS)
            self.photo_image = ImageTk.PhotoImage(image)
            self.scaled_size = (width, height)

        self.map_canvas.delete("all")
        self.coord_text = None
        self.coord_bg = None
        self.selection_rect = None
        self.map_canvas.create_image(0, 0, image=self.photo_image, anchor="nw", tags="map_image")
        self.map_canvas.configure(scrollregion=(0, 0, width, height))
        if self.missing_image_hint:
            self.map_canvas.create_text(width / 2, height / 2, text=self.missing_image_hint, fill="#ffe066",
                                        font=("Verdana", 12, "bold"), justify=tk.CENTER, tags="map_image")
        self.update_scale_display()
        self.display_spawns()

    def on_canvas_resize(self, event):
        """Refit the map (after the resize settles) when the canvas changes size"""
        if not self.fit_to_window or self.original_image is None:
            return
        if self.resize_job:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(150, self.refit_after_resize)

    def refit_after_resize(self):
        self.resize_job = None
        if self.fit_to_window:
            self.fit_map_to_window()

    def event_canvas_coords(self, event):
        """Mouse position of an event in canvas coordinates (includes the scroll offset)"""
        return self.map_canvas.canvasx(event.x), self.map_canvas.canvasy(event.y)

    def canvas_to_map_coords(self, canvas_x, canvas_y):
        """Convert canvas coordinates to map coordinates (0-255 range)"""
        # Zabezpieczenie przed dzieleniem przez zero
        if self.original_width <= 0 or self.original_height <= 0 or self.scale <= 0:
            return 0, 0
        
        # Convert canvas coordinates to original image coordinates
        raw_x = canvas_x / self.scale
        raw_y = canvas_y / self.scale
        
        # Convert to game coordinates (0-255 range): map X runs down the image, map Y to the right
        map_y = int(round((raw_x / self.original_width) * 255.0))
        map_x = int(round((raw_y / self.original_height) * 255.0))
        
        # Ensure coordinates stay within bounds
        map_x = max(0, min(255, map_x))
        map_y = max(0, min(255, map_y))
        
        return map_x, map_y

    def map_to_canvas_coords(self, map_x, map_y):
        """Convert map coordinates (0-255 range) to canvas coordinates"""
        # Zabezpieczenie przed dzieleniem przez zero
        if self.original_width <= 0 or self.original_height <= 0:
            return 0, 0
        
        # Convert from game coordinates (0-255) to image pixel coordinates
        raw_x = (map_y / 255.0) * self.original_width
        raw_y = (map_x / 255.0) * self.original_height
        
        return raw_x * self.scale, raw_y * self.scale

    def on_mouse_move(self, event):
        self.update_coord_overlay(*self.event_canvas_coords(event))

    def update_coord_overlay(self, canvas_x, canvas_y):
        """Show the map coordinates next to the cursor and in the status bar"""
        map_x, map_y = self.canvas_to_map_coords(canvas_x, canvas_y)
        # Update the coordinates in the status bar
        self.coordinates_var.set(f"X: {map_x} Y: {map_y}")
        # Remove old coordinate display if it exists
        self.remove_coord_overlay()
        
        # Format text with fixed width for better alignment
        text = f"X: {map_x:3d}  Y: {map_y:3d}"
        
        # Calculate text size (approximation) for better background sizing
        text_width = len(text) * 7  # Approximate width based on characters
        text_height = 20  # Fixed height for text
        
        # Create background rectangle with ample padding
        self.coord_bg = self.map_canvas.create_rectangle(
            canvas_x + 10,
            canvas_y - 30,
            canvas_x + 10 + text_width + 10,  # Add padding
            canvas_y - 30 + text_height + 10, # Add padding
            fill="#000066",     # Ciemnogranatowe tło
            outline="#FFFFFF",  # Biała ramka
            width=2,           # Grubsza ramka
            tags="coords"
        )
        
        # Create coordinate text centered on background
        self.coord_text = self.map_canvas.create_text(
            canvas_x + 15,
            canvas_y - 25,
            text=text,
            fill="#FFFFFF",     # Biały tekst
            font=("Arial", 12, "bold"),
            anchor="nw",
            tags="coords"
        )
        
        # Make sure the coordinate display is always on top
        self.map_canvas.tag_raise("coords")
        
    def remove_coord_overlay(self, event=None):
        if self.coord_text:
            self.map_canvas.delete(self.coord_text)
            self.coord_text = None
        if self.coord_bg:
            self.map_canvas.delete(self.coord_bg)
            self.coord_bg = None

    def on_mouse_down(self, event):
        # Focus the map so the arrow keys can nudge the selected spawn
        self.map_canvas.focus_set()
        # Usuwaj wszystkie tooltipy przy każdym kliknięciu na mapie
        self.hide_spawn_tooltip()
        canvas_x, canvas_y = self.event_canvas_coords(event)
        self.is_selecting = False
        self.drag_spawn_idx = None
        self.drag_moving = False
        self.pending_cycle = False

        # Kliknięto w istniejącego spawna: zaznacz go (przeciągnięcie go przesuwa)
        idx = self.spawn_index_at(canvas_x, canvas_y)
        if idx is not None:
            current = self.get_selected_spawn()
            if current is not None and self.spawn_pos(self.spawns[idx]) == self.spawn_pos(current):
                # Same spot as the selected spawn: keep it (so it can be dragged), cycle on release
                idx = self.selected_spawn_index
                self.pending_cycle = len(self.stacked_with(idx)) > 1
            else:
                self.select_spawn(idx)
            self.drag_spawn_idx = idx
            self.drag_start = (canvas_x, canvas_y)
            return
        
        # Ignore clicks next to the map image (they would add spawns on the map edge)
        if self.scaled_size and not (0 <= canvas_x <= self.scaled_size[0] and 0 <= canvas_y <= self.scaled_size[1]):
            return
        
        # Puste miejsce: kliknięcie dodaje spawn, przeciągnięcie dodaje obszar
        self.start_x = canvas_x
        self.start_y = canvas_y
        self.is_selecting = True

    def spawn_index_at(self, canvas_x, canvas_y, max_distance=8):
        """Index of the spawn drawn at a canvas point (dots before area outlines), or None"""
        area_hit = None
        items = self.map_canvas.find_overlapping(canvas_x - 2, canvas_y - 2, canvas_x + 2, canvas_y + 2)
        for item in reversed(items):  # Topmost first
            tags = self.map_canvas.gettags(item)
            idx = self.spawn_index_from_tags(tags)
            if idx is None:
                continue
            if "dot" in tags:
                return idx
            if area_hit is None:
                area_hit = idx
        # Jeśli kliknięto w pobliżu spawna, wybierz najbliższy
        nearest_idx = self.find_nearest_spawn(canvas_x, canvas_y, max_distance)
        return nearest_idx if nearest_idx is not None else area_hit

    def spawn_index_from_tags(self, tags):
        for tag in tags:
            if tag.startswith("spawn_") and tag[6:].isdigit():
                idx = int(tag[6:])
                return idx if idx < len(self.spawns) else None
        return None

    def find_nearest_spawn(self, canvas_x, canvas_y, max_distance=8):
        min_dist = float('inf')
        nearest_idx = None
        for i in self.visible_spawn_indices:
            spawn = self.spawns[i]
            sx, sy = self.map_to_canvas_coords(spawn['x'], spawn['y'])
            dist = ((canvas_x - sx) ** 2 + (canvas_y - sy) ** 2) ** 0.5
            if dist < min_dist and dist <= max_distance:
                min_dist = dist
                nearest_idx = i
        return nearest_idx

    @staticmethod
    def spawn_pos(spawn):
        return spawn['x'], spawn['y']

    def stacked_with(self, idx):
        """Indices of the visible spawns on the same spot as spawn idx (including idx)"""
        pos = self.spawn_pos(self.spawns[idx])
        return [i for i in sorted(self.visible_spawn_indices | {idx}) if self.spawn_pos(self.spawns[i]) == pos]

    def on_mouse_drag(self, event):
        canvas_x, canvas_y = self.event_canvas_coords(event)
        self.update_coord_overlay(canvas_x, canvas_y)

        # Przeciąganie istniejącego spawna
        if self.drag_spawn_idx is not None:
            start_x, start_y = self.drag_start
            if not self.drag_moving and abs(canvas_x - start_x) < 4 and abs(canvas_y - start_y) < 4:
                return
            self.drag_moving = True
            self.map_canvas.delete("drag_preview")
            self.map_canvas.create_line(start_x, start_y, canvas_x, canvas_y, fill="white", dash=(3, 3), tags="drag_preview")
            self.map_canvas.create_oval(canvas_x - 6, canvas_y - 6, canvas_x + 6, canvas_y + 6,
                                        outline="white", width=2, tags="drag_preview")
            return

        if not self.is_selecting:
            return
        
        if self.selection_rect:
            self.map_canvas.delete(self.selection_rect)
            
        self.selection_rect = self.map_canvas.create_rectangle(
            self.start_x, self.start_y, canvas_x, canvas_y,
            outline="blue", dash=(4, 4)
        )

    def on_mouse_up(self, event):
        canvas_x, canvas_y = self.event_canvas_coords(event)

        if self.drag_spawn_idx is not None:
            idx = self.drag_spawn_idx
            self.drag_spawn_idx = None
            self.map_canvas.delete("drag_preview")
            if self.drag_moving:
                self.drag_moving = False
                start_x, start_y = self.canvas_to_map_coords(*self.drag_start)
                end_x, end_y = self.canvas_to_map_coords(canvas_x, canvas_y)
                self.move_spawn(idx, end_x - start_x, end_y - start_y)
            elif self.pending_cycle:
                # Kolejne kliknięcie w stos wybiera następny spawn w tym miejscu
                stack = self.stacked_with(idx)
                next_idx = stack[(stack.index(idx) + 1) % len(stack)]
                self.select_spawn(next_idx)
                self.set_status(f"Stacked spawn {stack.index(next_idx) + 1} of {len(stack)} at X:{self.spawns[next_idx]['x']} "
                                f"Y:{self.spawns[next_idx]['y']} - click again for the next one")
            self.pending_cycle = False
            return

        if not self.is_selecting:
            return
        self.is_selecting = False
        if self.selection_rect:
            self.map_canvas.delete(self.selection_rect)
            self.selection_rect = None

        start = self.canvas_to_map_coords(self.start_x, self.start_y)
        # If it's a small area, treat as single click
        if abs(canvas_x - self.start_x) < 5 and abs(canvas_y - self.start_y) < 5:
            self.add_spawn_from_map(start)
        else:
            self.add_spawn_from_map(start, self.canvas_to_map_coords(canvas_x, canvas_y))
        
    def on_mouse_wheel(self, event):
        """Wheel scrolls the map, Shift+wheel scrolls sideways, Ctrl+wheel zooms at the cursor"""
        step = 1 if (event.num == 4 or getattr(event, 'delta', 0) > 0) else -1
        if event.state & 0x0004:  # Control
            self.zoom(1.25 if step > 0 else 0.8, event)
        elif event.state & 0x0001:  # Shift
            self.map_canvas.xview_scroll(-step, "units")
        else:
            self.map_canvas.yview_scroll(-step, "units")
        return "break"
        
    def on_right_click(self, event):
        """Context menu for the spawn under the cursor, or for an empty spot"""
        self.hide_spawn_tooltip()
        canvas_x, canvas_y = self.event_canvas_coords(event)
        map_x, map_y = self.canvas_to_map_coords(canvas_x, canvas_y)
        menu = tk.Menu(self.root, tearoff=0)

        idx = self.spawn_index_at(canvas_x, canvas_y)
        if idx is not None:
            self.select_spawn(idx)
            spawn = self.spawns[idx]
            monster_id = spawn['monster_id']
            menu.add_command(label=f"{self.get_monster_name(monster_id)} ({monster_id}) at X:{spawn['x']} Y:{spawn['y']}",
                             state="disabled")
            menu.add_separator()
            menu.add_command(label="Duplicate", command=self.duplicate_selected_spawn)
            menu.add_command(label="Delete", command=self.delete_selected_spawn)
            menu.add_command(label="Use This Monster for New Spawns", command=lambda: self.select_monster_for_adding(monster_id))
            menu.add_command(label="Copy Spawn Line", command=lambda: self.copy_to_clipboard(self.format_spawn_line(spawn)))
        else:
            if self.selected_monster_id is not None and self.selected_map_file:
                name = self.get_monster_name(self.selected_monster_id)
                menu.add_command(label=f"Add {name} Here", command=lambda: self.add_spawn_from_map((map_x, map_y)))
            else:
                menu.add_command(label="Select a monster to add spawns", state="disabled")
            if self.get_selected_spawn() is not None:
                menu.add_command(label="Move Selected Spawn Here", command=lambda: self.move_selected_spawn_to(map_x, map_y))
        menu.add_separator()
        menu.add_command(label=f"Copy Coordinates ({map_x} {map_y})", command=lambda: self.copy_to_clipboard(f"{map_x} {map_y}"))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        
    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status(f"Copied: {text}")

    def select_monster_for_adding(self, monster_id):
        """Select a monster in the 'New Mob Selection' list"""
        if not any(row.startswith(f"{monster_id}:") for row in self.monster_listbox.get(0, tk.END)):
            self.search_var.set("")  # The monster is hidden by the search filter
        for row, text in enumerate(self.monster_listbox.get(0, tk.END)):
            if text.startswith(f"{monster_id}:"):
                self.monster_listbox.selection_clear(0, tk.END)
                self.monster_listbox.selection_set(row)
                self.monster_listbox.see(row)
                self.on_monster_selected(None)
                return

    def add_spawn_from_map(self, start, end=None):
        """Add a spawn of the selected monster from a map click (start) or a drag (start to end)"""
        if not self.selected_map_file:
            self.set_status("Select a map first.")
            return
        if self.selected_monster_id is None or self.selected_monster_id not in self.monsters:
            self.set_status("Select a monster in 'New Mob Selection' first, then click on the map.")
            return
        section = self.get_new_spawn_section(self.selected_monster_id)
        if end is not None and section in AREA_SECTIONS:
            x, end_x = sorted((start[0], end[0]))
            y, end_y = sorted((start[1], end[1]))
            self.add_spawn(x, y, end_x, end_y, section=section)
        else:
            if end is not None:
                # Single-position spawn: use the centre of the dragged area
                start = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
            self.add_spawn(start[0], start[1], section=section)
        
    def get_new_spawn_section(self, monster_id):
        """Section for new spawns: the 'Add as' choice, or Auto (NPCs -> 0, others -> 1 area spawns)"""
        auto = 0 if self.get_monster_type(monster_id) == 0 else 1
        return self.parse_section_choice(self.new_section_var.get(), auto)
        
    def read_int(self, var, label, minimum, maximum):
        """Read a whole number from a Tk variable. Shows a warning and returns None if it is invalid."""
        try:
            value = int(var.get())
        except (tk.TclError, ValueError):
            messagebox.showwarning("Invalid Value", f"{label} must be a whole number.")
            return None
        if not minimum <= value <= maximum:
            messagebox.showwarning("Invalid Value", f"{label} must be between {minimum} and {maximum}.")
            return None
        return value

    def add_spawn(self, x, y, end_x=None, end_y=None, section=None):
        # Używaj zapamiętanych wyborów
        monster_id = self.selected_monster_id
        map_file = self.selected_map_file
        if monster_id is None or map_file is None:
            messagebox.showwarning("Warning", "Please select a map and a monster first.")
            return
        if section is None:
            section = self.get_new_spawn_section(monster_id)
        if end_x is None:
            end_x = x
        if end_y is None:
            end_y = y
        quantity = 1
        if section in AREA_SECTIONS:
            quantity = self.read_int(self.quantity_var, "Quantity", 1, 999)
            if quantity is None:
                return
        else:
            end_x, end_y = x, y
        spawn_range = self.read_int(self.range_var, "Range", 0, 255)
        if spawn_range is None:
            return

        # Save current state before adding
        self.save_state("Add Spawn")

        spawn = {
            'monster_id': monster_id,
            'map_number': self.get_map_number(map_file),
            'range': spawn_range,
            'x': x,
            'y': y,
            'end_x': end_x,
            'end_y': end_y,
            'direction': self.direction_var.get(),
            'quantity': quantity,
            'section': section
        }
        self.spawns.append(spawn)
        self.mark_modified()
        self.update_spawn_list()
        self.select_spawn(len(self.spawns) - 1)
        
        name = self.get_monster_name(monster_id)
        if (x, y) != (end_x, end_y):
            self.set_status(f"Added {name} x{quantity} in area X:{x}-{end_x} Y:{y}-{end_y} ({self.section_name(section)})")
        else:
            self.set_status(f"Added {name} at X:{x} Y:{y} ({self.section_name(section)})")

    def move_spawn(self, idx, dx, dy, coalesce=False):
        """Move a spawn and its area by dx, dy cells, keeping it inside the map"""
        if not 0 <= idx < len(self.spawns):
            return
        spawn = self.spawns[idx]
        dx = max(-min(spawn['x'], spawn['end_x']), min(255 - max(spawn['x'], spawn['end_x']), dx))
        dy = max(-min(spawn['y'], spawn['end_y']), min(255 - max(spawn['y'], spawn['end_y']), dy))
        if dx == 0 and dy == 0:
            return
        self.save_state("Move Spawn", coalesce_key=('move', idx) if coalesce else None)
        spawn['x'] += dx
        spawn['end_x'] += dx
        spawn['y'] += dy
        spawn['end_y'] += dy
        self.mark_modified()
        self.update_spawn_list()
        self.select_spawn(idx)
        self.set_status(f"Moved {self.get_monster_name(spawn['monster_id'])} to X:{spawn['x']} Y:{spawn['y']}")

    def move_selected_spawn_to(self, map_x, map_y):
        spawn = self.get_selected_spawn()
        if spawn is not None:
            self.move_spawn(self.selected_spawn_index, map_x - spawn['x'], map_y - spawn['y'])

    def nudge_selected_spawn(self, dx, dy):
        if self.get_selected_spawn() is not None:
            self.move_spawn(self.selected_spawn_index, dx, dy, coalesce=True)
        return "break"

    def get_selected_spawn(self):
        if 0 <= self.selected_spawn_index < len(self.spawns):
            return self.spawns[self.selected_spawn_index]
        return None

    def spawn_search_text(self):
        return self.spawn_search_var.get().lower().strip() if hasattr(self, 'spawn_search_var') else ""

    def spawn_matches(self, spawn, search_text):
        """Search by name, ID, npc / trap / monster, or coordinates like '130,143'"""
        coords = re.fullmatch(r'\(?\s*(\d+)\s*[, ]\s*(\d+)\s*\)?', search_text)
        if coords:
            return self.spawn_pos(spawn) == (int(coords.group(1)), int(coords.group(2)))
        type_word = {0: "npc", 1: "trap"}.get(self.get_monster_type(spawn['monster_id']), "monster")
        return (search_text in self.get_monster_name(spawn['monster_id']).lower() or
                search_text in str(spawn['monster_id']) or
                search_text in (type_word, type_word + "s"))

    def display_spawns(self):
        """Draw the spawns on the map, coloured by file section"""
        self.map_canvas.delete("spawn")
        self.remove_coord_overlay()
        self.visible_spawn_indices = set()
        # If hide_mobs is checked, don't display any spawns
        if hasattr(self, 'hide_mobs_var') and self.hide_mobs_var.get():
            return
        
        # Optionally show only the spawns matching the spawn list search (the selected one stays visible)
        search_text = self.spawn_search_text() if self.filter_map_var.get() else ""
        coord_counts = {}
        for i, spawn in enumerate(self.spawns):
            if search_text and i != self.selected_spawn_index and not self.spawn_matches(spawn, search_text):
                continue
            self.visible_spawn_indices.add(i)
            pos = self.spawn_pos(spawn)
            coord_counts[pos] = coord_counts.get(pos, 0) + 1

        # Areas first so the dots stay on top of them
        for i in sorted(self.visible_spawn_indices):
            spawn = self.spawns[i]
            if spawn['section'] in AREA_SECTIONS and (spawn['x'] != spawn['end_x'] or spawn['y'] != spawn['end_y']):
                is_selected = i == self.selected_spawn_index
                canvas_x, canvas_y = self.map_to_canvas_coords(spawn['x'], spawn['y'])
                canvas_end_x, canvas_end_y = self.map_to_canvas_coords(spawn['end_x'], spawn['end_y'])
                self.map_canvas.create_rectangle(
                    canvas_x, canvas_y, canvas_end_x, canvas_end_y,
                    outline="white" if is_selected else self.section_color(spawn['section']),
                    dash=(2, 2), width=2 if is_selected else 1,
                    tags=("spawn", f"spawn_{i}", "area")
                )

        for i in sorted(self.visible_spawn_indices):
            spawn = self.spawns[i]
            canvas_x, canvas_y = self.map_to_canvas_coords(spawn['x'], spawn['y'])
            is_selected = i == self.selected_spawn_index
            # Only the selected spawn gets the big highlight
            radius = 6 if is_selected else 4
            self.map_canvas.create_oval(
                canvas_x-radius, canvas_y-radius,
                canvas_x+radius, canvas_y+radius,
                fill=self.section_color(spawn['section']), outline="white" if is_selected else "black", width=2,
                tags=("spawn", f"spawn_{i}", "dot")
            )
            
        # Draw stack counts above spots with several spawns
        for (mx, my), count in coord_counts.items():
            if count > 1:
                cx, cy = self.map_to_canvas_coords(mx, my)
                self.map_canvas.create_text(
                    cx, cy - 8, 
                    text=f"x{count}",
                    fill="white",
                    font=("Segoe UI", 8, "bold"),
                    tags="spawn"
                )

        # Raise the selected spawn so it is drawn and clicked first
        if self.selected_spawn_index in self.visible_spawn_indices:
            self.map_canvas.tag_raise(f"spawn_{self.selected_spawn_index}")

    def on_spawn_hover(self, event):
        items = self.map_canvas.find_withtag(tk.CURRENT)
        if not items:
            return
        idx = self.spawn_index_from_tags(self.map_canvas.gettags(items[0]))
        if idx is not None:
            self.show_spawn_tooltip(idx)
        
    def show_spawn_tooltip(self, idx):
        """Show tooltip with monster information when hovering over a spawn point"""
        self.hide_spawn_tooltip()  # Zawsze chowaj poprzedni tooltip
        spawn = self.spawns[idx]
        monster_id = spawn['monster_id']
        type_name = {0: "NPC", 1: "Trap"}.get(self.get_monster_type(monster_id), "Monster")
        lines = [f"{self.get_monster_name(monster_id)} ({type_name})",
                 f"ID: {monster_id}",
                 f"Section: {self.section_label(spawn['section'])}"]
        if spawn['section'] in AREA_SECTIONS:
            lines.append(f"Area: ({spawn['x']}, {spawn['y']}) - ({spawn['end_x']}, {spawn['end_y']}) [0-255]")
            lines.append(f"Quantity: {spawn['quantity']}")
        else:
            lines.append(f"Pos: ({spawn['x']}, {spawn['y']}) [0-255]")
        lines.append(f"Range: {spawn['range']}   Direction: {spawn['direction']}")
        stack_count = len(self.stacked_with(idx))
        if stack_count > 1:
            lines.append(f"Stacked: {stack_count} spawns here (click again to cycle)")
        
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        self.tooltip = tk.Toplevel()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x+10}+{y+10}")
        label = tk.Label(self.tooltip, text="\n".join(lines), justify=tk.LEFT,
                         background="#ffffe0", foreground="#000000", relief=tk.SOLID, borderwidth=1)
        label.pack()

    def hide_spawn_tooltip(self, event=None):
        """Hide the tooltip window"""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def select_spawn(self, idx, scroll_map=False):
        """Select a spawn: highlight it on the map and in the list and load it into Spawn Properties.
        The 'New Mob Selection' inputs are left alone, so new spawns still use the monster chosen there."""
        if not 0 <= idx < len(self.spawns):
            self.clear_spawn_selection()
            return
        self.selected_spawn_index = idx
        spawn = self.spawns[idx]

        # Aktualizuj pola koordynatów
        self.spawn_x_var.set(spawn['x'])
        self.spawn_y_var.set(spawn['y'])
        self.spawn_end_x_var.set(spawn['end_x'])
        self.spawn_end_y_var.set(spawn['end_y'])
        self.spawn_qty_var.set(spawn['quantity'])
        self.spawn_range_var.set(spawn['range'])
        self.spawn_dir_var.set(spawn['direction'])
        self.spawn_section_var.set(self.section_label(spawn['section']))
        self.update_spawn_props_state()

        # Pokaż ramkę z koordynatami
        self.spawn_coords_frame.grid()

        # Załaduj również statystyki moba
        self.show_monster_stats(spawn['monster_id'])

        self.highlight_spawn_in_list(idx)
        self.display_spawns()
        if scroll_map:
            self.scroll_map_to_spawn(idx)

        message = f"Selected {self.get_monster_name(spawn['monster_id'])} at X:{spawn['x']} Y:{spawn['y']}"
        stack_count = len(self.stacked_with(idx))
        if stack_count > 1:
            message += f" - {stack_count} spawns stacked here, click again to cycle"
        self.set_status(message)

    def clear_spawn_selection(self, redraw=True):
        self.selected_spawn_index = -1
        if hasattr(self, 'spawn_coords_frame'):
            self.spawn_coords_frame.grid_remove()
        if hasattr(self, 'spawn_listbox'):
            self.spawn_listbox.selection_clear(0, tk.END)
        if redraw:
            self.display_spawns()

    def update_spawn_props_state(self):
        """End position and quantity can only be edited for area sections"""
        section = self.parse_section_choice(self.spawn_section_var.get(), 1)
        state = "normal" if section in AREA_SECTIONS else "disabled"
        for widget in self.spawn_area_widgets:
            widget.configure(state=state)

    def highlight_spawn_in_list(self, idx):
        self.spawn_listbox.selection_clear(0, tk.END)
        if idx in self.spawn_list_rows:
            row = self.spawn_list_rows.index(idx)
            self.spawn_listbox.selection_set(row)
            self.spawn_listbox.activate(row)
            self.spawn_listbox.see(row)

    def scroll_map_to_spawn(self, idx):
        """Scroll a zoomed-in map so the spawn is in the middle of the view"""
        if not self.scaled_size:
            return
        width, height = self.scaled_size
        canvas_x, canvas_y = self.map_to_canvas_coords(self.spawns[idx]['x'], self.spawns[idx]['y'])
        view_width = self.map_canvas.winfo_width()
        view_height = self.map_canvas.winfo_height()
        if width > view_width:
            self.map_canvas.xview_moveto(max(0.0, (canvas_x - view_width / 2) / width))
        if height > view_height:
            self.map_canvas.yview_moveto(max(0.0, (canvas_y - view_height / 2) / height))

    def show_monster_stats(self, monster_id):
        """Show a monster's stats in the 'Selected Monster Stats' panel"""
        self.stats_monster_id = monster_id
        stats = self.monster_stats.get(monster_id)
        for key, var in self.stat_vars.items():
            var.set(str(stats.get(key, 0)) if stats else "0")
        if not stats:
            # Jeśli brak statystyk, wyświetl chociaż podstawowe dane
            self.stat_vars['name'].set(self.get_monster_name(monster_id))
            self.stat_vars['id'].set(str(monster_id))
        self.mob_type_var.set(self.get_monster_type(monster_id))

    def on_monster_selected(self, event):
        selection = self.monster_listbox.curselection()
        if not selection:
            return
        monster_text = self.monster_listbox.get(selection[0])
        if monster_text.startswith("==="):
            return
            
        # Extract monster ID from the text (format: "123: 🧍 Monster Name")
        try:
            monster_id = int(monster_text.split(":")[0])
        except ValueError:
            return
        self.selected_monster_id = monster_id
        self.show_monster_stats(monster_id)
                
        # NPCs are always placed one at a time
        if self.get_monster_type(monster_id) == 0:
            self.quantity_spinbox.configure(state='disabled')
            self.quantity_var.set(1)
        else:
            self.quantity_spinbox.configure(state='normal')
                    
        self.set_status(f"New spawns: {self.get_monster_name(monster_id)} - click the map to add one, drag to add an area")

    def filter_monsters(self, *args):
        self.update_monster_list()

    def update_monster_list(self):
        """Update the monster list based on search text"""
        self.monster_listbox.delete(0, tk.END)
        search_text = self.search_var.get().lower()
        
        # Create lists for different monster types
        npcs = []
        monsters = []
        
        for monster_id, monster_data in self.monsters.items():
            # Update the type from the more accurate data in monster_stats
            if monster_id in self.monster_stats:
                monster_data['type'] = self.monster_stats[monster_id]['type']
            
            # Filter based on search text
            if search_text in monster_data['name'].lower() or search_text in str(monster_id):
                if monster_data.get('type', 2) == 0:
                    npcs.append((monster_id, monster_data['name']))
                else:
                    monsters.append((monster_id, monster_data['name']))
        
        selected_row = None
        # Add NPCs section
        if npcs:
            self.monster_listbox.insert(tk.END, "=== NPCs ===")
            for monster_id, name in sorted(npcs):
                if monster_id == self.selected_monster_id:
                    selected_row = self.monster_listbox.size()
                self.monster_listbox.insert(tk.END, f"{monster_id}: 🧍 {name}")
        
        # Add Monsters & Traps section
        if monsters:
            self.monster_listbox.insert(tk.END, "=== Monsters ===")
            for monster_id, name in sorted(monsters):
                if monster_id == self.selected_monster_id:
                    selected_row = self.monster_listbox.size()
                type_symbol = "⚠️" if self.get_monster_type(monster_id) == 1 else "👹"
                self.monster_listbox.insert(tk.END, f"{monster_id}: {type_symbol} {name}")
                
        # Keep the monster chosen for new spawns highlighted
        if selected_row is not None:
            self.monster_listbox.selection_set(selected_row)
            self.monster_listbox.see(selected_row)

    def format_spawn_line(self, spawn):
        """One line of a MonsterSetBase file"""
        line = (f"{spawn['monster_id']:<14}{spawn['map_number']:<14}{spawn['range']:<12}"
                f"{spawn['x']:<14}{spawn['y']:<14}")
        if spawn['section'] in AREA_SECTIONS:
            line += f"{spawn['end_x']:<14}{spawn['end_y']:<14}{spawn['direction']:<14}{spawn['quantity']:<14}"
        else:
            line += f"{spawn['direction']:<14}"
        return line + f"//{self.get_monster_name(spawn['monster_id'])}"

    def write_spawn_file(self, filename, spawns):
        """Write spawns to a MonsterSetBase file, one block per section (0 and 1 are always written)"""
        sections = sorted({0, 1} | {spawn['section'] for spawn in spawns})
        temp_filename = filename + ".tmp"
        with open(temp_filename, 'w', errors='replace') as f:
            for n, section in enumerate(sections):
                if n:
                    f.write("\n")
                f.write(SECTION_SEPARATOR + "\n")
                f.write("// NPCS\n" if section == 0 else "// MONSTERS\n")
                f.write(SECTION_SEPARATOR + "\n")
                f.write(f"{section}\n")
                if section in AREA_SECTIONS:
                    f.write("//Monster      MapNumber      Range      BeginPosX      BeginPosY      EndPosX      EndPosY      Direction      Quantity      Comment\n")
                else:
                    f.write("//Monster      MapNumber      Range      PositionX      PositionY      Direction      Comment\n")
                for spawn in spawns:
                    if spawn['section'] == section:
                        f.write(self.format_spawn_line(spawn) + "\n")
                f.write("end\n")
        # Replace the file only once it was written completely
        os.replace(temp_filename, filename)

    def backup_file(self, filename):
        """Copy a file to <name>.bak the first time it is overwritten in this session"""
        if filename in self.backed_up_files or not os.path.exists(filename):
            return ""
        shutil.copy2(filename, filename + ".bak")
        self.backed_up_files.add(filename)
        return f" (original kept as {os.path.basename(filename)}.bak)"

    def save_changes(self, map_file=None):
        """Save a map (the current one by default) to MonsterSetBase. Returns True on success."""
        if map_file is None:
            map_file = self.selected_map_file
        if not map_file:
            messagebox.showwarning("Warning", "Please select a map first")
            return False
        if map_file == self.selected_map_file:
            self.save_map_to_memory(map_file)
        spawns = self.map_spawns.get(map_file, [])
        filename = os.path.join("MonsterSetBase", map_file)
        try:
            backup_note = self.backup_file(filename)
            self.write_spawn_file(filename, spawns)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {map_file}: {str(e)}")
            return False
                
        # Remove from modified maps list after saving
        self.modified_maps.discard(map_file)
        self.update_modified_indicator()
        self.refresh_map_list()
        self.set_status(f"Saved {map_file}{backup_note}")
        return True
                
    def save_all_changes(self):
        """Save every map with unsaved changes. Returns True if all of them were saved."""
        if self.selected_map_file:
            self.save_map_to_memory(self.selected_map_file)
        if not self.modified_maps:
            self.set_status("No unsaved changes")
            return True
        saved = [map_file for map_file in sorted(self.modified_maps) if self.save_changes(map_file)]
        if self.modified_maps:
            return False
        self.set_status(f"Saved {len(saved)} map(s): {', '.join(saved)}")
        return True

    def on_map_selected(self, event):
        selection = self.map_listbox.curselection()
        if selection and selection[0] < len(self.map_list_rows):
            self.open_map(self.map_list_rows[selection[0]])
                
    def on_spawn_search_changed(self, *args):
        self.update_spawn_list()
        if self.filter_map_var.get():
            self.display_spawns()
                
    def format_spawn_entry(self, spawn):
        """Text of a spawn in the 'Mobs on Selected Map' list"""
        name = self.get_monster_name(spawn['monster_id'])
        icon = {0: "🧍", 1: "⚠️"}.get(self.get_monster_type(spawn['monster_id']), "👹")
        if spawn['section'] in AREA_SECTIONS:
            return (f"({spawn['x']}, {spawn['y']}) {icon} {name} - Qty: {spawn['quantity']} - "
                    f"Area: ({spawn['x']}, {spawn['y']}) to ({spawn['end_x']}, {spawn['end_y']})")
        entry = f"({spawn['x']}, {spawn['y']}) {icon} {name}"
        if spawn['range']:
            entry += f" - Range: {spawn['range']}"
        return entry

    def update_spawn_list(self, *args):
        """Fill the spawn list grouped by section and sorted by position, applying the search filter"""
        self.spawn_listbox.delete(0, tk.END)
        self.spawn_list_rows = []
        search_text = self.spawn_search_text()

        by_section = {}
        for i, spawn in enumerate(self.spawns):
            by_section.setdefault(spawn['section'], []).append(i)

        shown = 0
        for section in sorted(by_section):
            indices = [i for i in by_section[section]
                       if not search_text or self.spawn_matches(self.spawns[i], search_text)]
            if not indices:
                continue
            # Sort by coordinate X, Y for better grouping
            indices.sort(key=lambda i: self.spawn_pos(self.spawns[i]))
            self.spawn_listbox.insert(tk.END, f"=== {self.section_label(section)} ({len(indices)}) ===")
            self.spawn_list_rows.append(None)
            for i in indices:
                self.spawn_listbox.insert(tk.END, self.format_spawn_entry(self.spawns[i]))
                self.spawn_list_rows.append(i)
            shown += len(indices)

        npc_section = len(by_section.get(0, []))
        monster_total = sum(spawn['quantity'] for spawn in self.spawns if spawn['section'] != 0)
        summary = f"{len(self.spawns)} entries ({npc_section} in NPC section, {monster_total} monsters in total)"
        if search_text:
            summary = f"Showing {shown} of {summary}"
        self.spawn_summary_var.set(summary)

        if self.selected_spawn_index >= 0:
            self.highlight_spawn_in_list(self.selected_spawn_index)

    def on_spawn_selected(self, event):
        """Handle spawn selection in the list"""
        selection = self.spawn_listbox.curselection()
        if not selection or selection[0] >= len(self.spawn_list_rows):
            return
        spawn_index = self.spawn_list_rows[selection[0]]
        if spawn_index is not None:
            self.select_spawn(spawn_index, scroll_map=True)

    def duplicate_selected_spawn(self):
        """Add a copy of the selected spawn on the same spot"""
        spawn = self.get_selected_spawn()
        if spawn is None:
            self.set_status("Select a spawn to duplicate first.")
            return
        self.save_state("Duplicate Spawn")
        self.spawns.append(copy.deepcopy(spawn))
        self.mark_modified()
        self.update_spawn_list()
        self.select_spawn(len(self.spawns) - 1)
        self.set_status("Spawn duplicated - drag it on the map (or use the arrow keys) to move it")

    def delete_selected_spawn(self):
        """Delete the currently selected spawn"""
        spawn = self.get_selected_spawn()
        if spawn is None:
            self.set_status("Select a spawn to delete first.")
            return
        # Save current state before deleting
        self.save_state("Remove Spawn")
            
        # Remove the spawn
        del self.spawns[self.selected_spawn_index]
        self.clear_spawn_selection(redraw=False)
            
        # Update the display
        self.mark_modified()
        self.update_spawn_list()
        self.display_spawns()
        self.set_status(f"Removed {self.get_monster_name(spawn['monster_id'])} at X:{spawn['x']} Y:{spawn['y']} (Ctrl+Z to undo)")

    def toggle_mobs_visibility(self):
        """Toggle the visibility of mobs on the map"""
        self.view_mobs_var.set(not self.hide_mobs_var.get())
        self.display_spawns()

    def update_monster_stats(self):
        """Update the monster stats based on the UI values"""
        monster_id = self.stats_monster_id
        if monster_id is None:
            messagebox.showwarning("Warning", "No monster selected to update")
            return
            
        # Collect all values from the UI
        updated_stats = {}
        for key, var in self.stat_vars.items():
            if key == "name":
                updated_stats[key] = var.get()
                continue
            try:
                updated_stats[key] = int(var.get()) if var.get().strip() else 0
            except ValueError:
                messagebox.showwarning("Warning", f"Invalid value for {key}: {var.get()}")
                return
        
        # Update the monster stats in memory
        monster_type = self.mob_type_var.get()
        stats = self.monster_stats.setdefault(monster_id, {})
        stats.update(updated_stats)
        stats['id'] = monster_id
        stats['type'] = monster_type
        monster = self.monsters.setdefault(monster_id, {})
        monster['name'] = updated_stats['name']
        monster['type'] = monster_type
        
        # Refresh the monster list and spawns
        self.update_monster_list()
        self.update_spawn_list()
        self.display_spawns()
        self.set_status(f"Monster {monster_id} updated in the editor (Monster.txt itself is not changed)")

    def update_direction_label(self):
        value = self.direction_var.get()
        self.direction_label_var.set(f"Selected direction: {value}")

    def show_instructions(self):
        instructions = """
Monster & MonsterSetBase Editor - Instructions

1. Select a map from the Map Selection panel (type in Search to filter)
2. Choose a monster in 'New Mob Selection'
3. On the map:
   - Click an empty spot: add one spawn of that monster
   - Drag over an empty area: add an area spawn
   - Click a spawn: select it and edit it in 'Spawn Properties'
   - Click a stacked spawn (xN) again: select the next one on that spot
   - Drag a spawn: move it (its area moves with it)
   - Right-click: duplicate, delete, move here, copy coordinates
4. 'Add as' chooses the file section for new spawns
   (Auto: NPCs go to section 0, monsters to section 1 area spawns)
5. Quantity, Range and Direction apply to new spawns
6. Save with File > Save (Ctrl+S) or Save All (Ctrl+Shift+S)

Tips:
- Spawn search accepts a name, an ID, npc / trap / monster
  or coordinates like 130,143
- 'Show only search results on map' hides everything else
- Edits stay in memory when you switch maps; maps with unsaved
  changes are marked with *
- The first save of a file in a session keeps the original as .bak
        """
        messagebox.showinfo("Instructions", instructions)
        
    def show_shortcuts(self):
        shortcuts = """
Ctrl+O                  Load map file
Ctrl+S                  Save current map
Ctrl+Shift+S         Save all modified maps
Ctrl+Z / Ctrl+Y      Undo / Redo
Ctrl+D                  Duplicate selected spawn
Delete                   Delete selected spawn
Esc                       Clear selection
Arrow keys            Nudge selected spawn (click the map first)

Ctrl+Wheel, Ctrl +/-  Zoom
Ctrl+0                  Fit map to window
Ctrl+1                  Actual size (100%)
Wheel / Shift+Wheel  Scroll the map
Middle mouse drag   Pan the map
Right-click             Spawn / map menu
        """
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)

    def show_about(self):
        about_text = f"""
Monster & MonsterSetBase Editor
Version: {APP_VERSION}
Dedicated for Season 6 files by Louis

Created by Shizoo
Modifications by Popoman
A visual editor for MU Online monster spawn files.
        """
        messagebox.showinfo("About", about_text)

    def update_selected_spawn(self):
        """Update the properties of the selected spawn"""
        spawn = self.get_selected_spawn()
        if spawn is None:
            messagebox.showwarning("Warning", "No spawn selected to update")
            return
            
        # Pobierz i sprawdź wartości z pól przed jakąkolwiek zmianą
        fields = [
            ('x', self.spawn_x_var, "Start X", 0, 255),
            ('y', self.spawn_y_var, "Start Y", 0, 255),
            ('end_x', self.spawn_end_x_var, "End X", 0, 255),
            ('end_y', self.spawn_end_y_var, "End Y", 0, 255),
            ('quantity', self.spawn_qty_var, "Quantity", 1, 999),
            ('range', self.spawn_range_var, "Range", 0, 255),
            ('direction', self.spawn_dir_var, "Direction", -1, 8),
        ]
        section = self.parse_section_choice(self.spawn_section_var.get(), spawn['section'])
        values = {'section': section}
        for key, var, label, minimum, maximum in fields:
            if section not in AREA_SECTIONS and key in ('end_x', 'end_y', 'quantity'):
                continue  # Not used by single-position sections
            value = self.read_int(var, label, minimum, maximum)
            if value is None:
                return
            values[key] = value
            
        if section in AREA_SECTIONS:
            # Keep the start in the top-left corner of the area
            values['x'], values['end_x'] = sorted((values['x'], values['end_x']))
            values['y'], values['end_y'] = sorted((values['y'], values['end_y']))
        else:
            # Dla pojedynczych pozycji koniec jest równy początkowi
            values['end_x'], values['end_y'], values['quantity'] = values['x'], values['y'], 1
            
        if all(spawn[key] == value for key, value in values.items()):
            self.set_status("Nothing to update - the spawn already has these values")
            return
            
        # Save current state before updating
        self.save_state("Update Spawn")
        spawn.update(values)
            
        # Odśwież listę i wyświetlanie
        self.mark_modified()
        self.update_spawn_list()
        self.select_spawn(self.selected_spawn_index)
        self.set_status("Spawn updated")

    def toggle_mobs_visibility_menu(self):
        """Toggle visibility of mobs from menu"""
        self.hide_mobs_var.set(not self.view_mobs_var.get())
        self.display_spawns()

    def zoom(self, factor, event=None):
        """Zoom by factor, keeping the point under the mouse (or the middle of the view) in place"""
        if self.original_image is None:
            return
        new_scale = max(0.1, min(8.0, self.scale * factor))
        if abs(new_scale - self.scale) < 1e-9:
            return
        if event is not None:
            view_x, view_y = event.x, event.y
        else:
            view_x = self.map_canvas.winfo_width() / 2
            view_y = self.map_canvas.winfo_height() / 2
        image_x = self.map_canvas.canvasx(view_x) / self.scale
        image_y = self.map_canvas.canvasy(view_y) / self.scale

        self.scale = new_scale
        self.fit_to_window = False
        self.render_map()

        width, height = self.scaled_size
        self.map_canvas.xview_moveto(max(0.0, (image_x * new_scale - view_x) / width))
        self.map_canvas.yview_moveto(max(0.0, (image_y * new_scale - view_y) / height))

    def zoom_in(self):
        """Increase map zoom by 25%"""
        self.zoom(1.25)

    def zoom_out(self):
        """Decrease map zoom by 20%"""
        self.zoom(0.8)

    def reset_zoom(self):
        """Fit the whole map into the window"""
        self.fit_map_to_window()

    def actual_size(self):
        """Show the map image at 100%"""
        if self.scale > 0:
            self.zoom(1.0 / self.scale)

    def update_scale_display(self):
        """Update scale indicator in status bar"""
        scale_percent = int(round(self.scale * 100))
        self.scale_var.set(f"Scale: {scale_percent}%" + (" (fit)" if self.fit_to_window else ""))

    # Undo/redo functionality
    def save_state(self, action_name, coalesce_key=None):
        """Save current state to undo stack.
        Consecutive actions with the same coalesce_key (e.g. arrow key nudges) are undone in one step."""
        if (coalesce_key is not None and self.undo_stack and not self.redo_stack and
                self.undo_stack[-1].get('coalesce_key') == coalesce_key):
            return
        
        # Create a copy of current spawns for the undo stack
        current_state = {
            'spawns': copy.deepcopy(self.spawns),
            'action': action_name,
            'selected_spawn_index': self.selected_spawn_index,
            'coalesce_key': coalesce_key
        }
        
        # Add to undo stack and clear redo stack (since we're creating a new action path)
        self.undo_stack.append(current_state)
        self.redo_stack.clear()
        
        # Limit the size of the undo stack
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        
        # Update menu states
        self.update_undo_redo_states()

    def update_undo_redo_states(self):
        """Update the enabled/disabled state of undo/redo menu items"""
        if hasattr(self, 'edit_menu'):
            try:
                # Update Undo state
                if self.undo_stack:
                    action = self.undo_stack[-1]['action']
                    self.edit_menu.entryconfigure(self.undo_index, state="normal")
                    self.edit_menu.entryconfigure(self.undo_index, label=f"Undo {action}")
                else:
                    self.edit_menu.entryconfigure(self.undo_index, state="disabled")
                    self.edit_menu.entryconfigure(self.undo_index, label="Undo")
                
                # Update Redo state
                if self.redo_stack:
                    action = self.redo_stack[-1]['action']
                    self.edit_menu.entryconfigure(self.redo_index, state="normal")
                    self.edit_menu.entryconfigure(self.redo_index, label=f"Redo {action}")
                else:
                    self.edit_menu.entryconfigure(self.redo_index, state="disabled")
                    self.edit_menu.entryconfigure(self.redo_index, label="Redo")
            except Exception as e:
                print(f"Error updating menu state: {e}")
                # Don't let a menu error crash the whole application

    def restore_state(self, state):
        """Show the spawns of an undo/redo state"""
        self.spawns = state['spawns']
        self.mark_modified()
        self.update_spawn_list()
        if 0 <= state.get('selected_spawn_index', -1) < len(self.spawns):
            self.select_spawn(state['selected_spawn_index'])
        else:
            self.clear_spawn_selection()
        self.update_undo_redo_states()

    def undo(self):
        """Restore the previous state from undo stack"""
        if not self.undo_stack:
            self.set_status("Nothing to undo")
            return
        previous_state = self.undo_stack.pop()
        self.redo_stack.append({
            'spawns': copy.deepcopy(self.spawns),
            'action': previous_state['action'],
            'selected_spawn_index': self.selected_spawn_index
        })
        self.restore_state(previous_state)
        self.set_status(f"Undid: {previous_state['action']}")

    def redo(self):
        """Restore the next state from redo stack"""
        if not self.redo_stack:
            self.set_status("Nothing to redo")
            return
        next_state = self.redo_stack.pop()
        self.undo_stack.append({
            'spawns': copy.deepcopy(self.spawns),
            'action': next_state['action'],
            'selected_spawn_index': self.selected_spawn_index
        })
        self.restore_state(next_state)
        self.set_status(f"Redid: {next_state['action']}")

    def save_map_to_memory(self, map_file):
        """Save current map spawns to memory (also when every spawn was removed)"""
        self.map_spawns[map_file] = copy.deepcopy(self.spawns)

    def on_closing(self):
        """Handle application closing with unsaved changes check"""
        if self.modified_maps:
            # Format list of modified maps for display
            modified_list = "\n".join(sorted(self.modified_maps))
            
            # Ask user if they want to save changes before exiting
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                f"You have unsaved changes on the following maps:\n\n{modified_list}\n\nDo you want to save these changes before exiting?",
                icon="warning"
            )
            
            if result is None:  # Cancel
                return  # Don't close the app
            if result and not self.save_all_changes():
                return  # Keep the editor open if a map could not be saved
        
        # Close the application
        self.root.destroy()

def get_app_dir():
    """Folder that holds Monster/, MonsterSetBase/ and Images/"""
    if getattr(sys, 'frozen', False):  # Built with PyInstaller
        return os.path.dirname(os.path.abspath(sys.executable))
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) == 'src':
        return os.path.dirname(script_dir)
    return script_dir

def main():
    # Find the data folders next to the program, whatever folder it was started from
    os.chdir(get_app_dir())
        
    root = tk.Tk()
    app = MonsterSpawnEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()

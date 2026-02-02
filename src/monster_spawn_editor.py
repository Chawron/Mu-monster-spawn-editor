import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import os
import re
import random
import copy  # For deep copying spawns for undo/redo functionality

class MonsterSpawnEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Monster & MonsterSetBase Editor by Shizoo")
        
        # Set program icon if available
        self.set_program_icon()
        
        # Initialize undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 20  # Maximum number of actions to keep in history
        
        # Dictionary to store spawns for each map
        self.map_spawns = {}
        self.modified_maps = set()  # Track which maps have been modified
        
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
        
        # Set minimum window size and maximize on start
        self.root.minsize(1200, 800)
        self.root.state('zoomed')
        
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
        self.current_map_image = None
        self.photo_image = None
        self.original_width = 0
        self.original_height = 0
        self.scale = 1.0  # Default scale
        
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
        
        # Selection rectangle variables
        self.start_x = None
        self.start_y = None
        self.selection_rect = None
        self.is_selecting = False
        
        # Store spawns
        self.spawns = []
        
        # Coordinate display variables
        self.coord_text = None
        self.coord_bg = None
        
        # Bind closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def set_program_icon(self):
        """Set the program icon if the icon file exists"""
        icon_path = "icon.ico"
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
            # Dla Windows, ustaw także ikonę w pasku zadań
            try:
                import ctypes
                myappid = f'shizoo.monsterspawneditor.1.0'  # arbitrary string
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception as e:
                print(f"Warning: Could not set taskbar icon: {str(e)}")
        else:
            print("Icon file not found. Place 'icon.ico' in the program directory to set custom icon.")

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
                            
                            # Debug output for important monsters
                            if "spider" in full_name.lower():
                                print(f"Found Spider in load_monster_data: ID={monster_id}, Name={full_name}, InitialType={monster_type}")
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
        edit_menu.add_command(label="Delete Selected Spawn", command=self.delete_selected_spawn, accelerator="Del")
        
        self.edit_menu = edit_menu  # Store reference to edit menu
        
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Opcja do pokazania/ukrycia mobów
        self.view_mobs_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Show Mobs", variable=self.view_mobs_var, command=self.toggle_mobs_visibility_menu)
        
        # Opcje zmiany skali
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Reset Zoom", command=self.reset_zoom, accelerator="Ctrl+0")
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Instructions", command=self.show_instructions)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Bind keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self.load_map_dialog())
        self.root.bind("<Control-s>", lambda e: self.save_changes())
        self.root.bind("<Delete>", lambda e: self.delete_selected_spawn())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())  # Dla klawiatury amerykańskiej
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.reset_zoom())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())

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
        map_frame.rowconfigure(0, weight=1)
        
        # Map list with scrollbar
        map_list_frame = ttk.Frame(map_frame)
        map_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        map_list_frame.columnconfigure(0, weight=1)
        map_list_frame.rowconfigure(0, weight=1)
        
        self.map_listbox = tk.Listbox(map_list_frame, height=10, width=30)
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
        
        self.monster_listbox = tk.Listbox(monster_list_frame, height=10, width=25)
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
        spawn_coords_frame = ttk.LabelFrame(stats_container, text="Spawn Properties")
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
        spawn_qty_entry = tk.Spinbox(spawn_coords_frame, from_=1, to=100, textvariable=self.spawn_qty_var, width=5,
            background='#23293a', foreground='#e0e6f8', insertbackground='#e0e6f8', font=('Verdana', 10, 'bold'),
            highlightbackground='#bfa14a', highlightcolor='#ffe066', relief='flat', borderwidth=2)
        spawn_qty_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(spawn_coords_frame, text="Range:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        spawn_range_entry = tk.Spinbox(spawn_coords_frame, from_=0, to=100, textvariable=self.spawn_range_var, width=5,
            background='#23293a', foreground='#e0e6f8', insertbackground='#e0e6f8', font=('Verdana', 10, 'bold'),
            highlightbackground='#bfa14a', highlightcolor='#ffe066', relief='flat', borderwidth=2)
        spawn_range_entry.grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Przycisk do aktualizacji
        update_coords_button = ttk.Button(spawn_coords_frame, text="Update Spawn", command=self.update_selected_spawn)
        update_coords_button.grid(row=3, column=0, columnspan=4, sticky=tk.E, padx=5, pady=5)
        
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
        direction_frame = ttk.LabelFrame(controls_frame, text="Direction")
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
        
        # Mob type selection
        mob_type_frame = ttk.LabelFrame(controls_frame, text="Mob Type")
        mob_type_frame.grid(row=0, column=1, sticky=(tk.W, tk.N, tk.E), padx=(5, 0), pady=5)
        
        self.mob_type_var = tk.IntVar(value=2)  # Default to Standard
        
        # Create radio buttons for mob types in a more compact layout
        mob_types = [
            (0, "NPC", "yellow"),
            (2, "Standard", "red"),
            (1, "Multiple", "blue"),
            (3, "Multiple", "green"),
            (4, "Event", "cyan")
        ]
        
        for i, (value, text, color) in enumerate(mob_types):
            frame = ttk.Frame(mob_type_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            
            # Create colored indicator
            color_indicator = tk.Label(frame, text="", bg=color, width=2, height=1)
            color_indicator.grid(row=0, column=0, padx=5)
            
            # Create radio button
            rb = tk.Radiobutton(frame, text=f"({value}) {text}", variable=self.mob_type_var, value=value)
            rb.grid(row=0, column=1, sticky=tk.W)

    def create_map_view(self):
        map_frame = ttk.LabelFrame(self.right_panel, text="Map View")
        map_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure map frame for resizing - POPRAWIONA RESPONSYWNOŚĆ
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(0, weight=1)
        map_frame.rowconfigure(1, weight=0)  # Scrollbar horyzontalny ma stałą wysokość
        
        # Canvas for map with frame for proper resizing
        canvas_frame = ttk.Frame(map_frame)
        canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        # Canvas for map - DODANO MIN SIZE DLA POPRAWY RESPONSYWNOŚCI
        self.map_canvas = tk.Canvas(canvas_frame, width=800, height=600, bg="light gray")
        self.map_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbars
        x_scroll = ttk.Scrollbar(map_frame, orient="horizontal", command=self.map_canvas.xview)
        x_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        y_scroll = ttk.Scrollbar(map_frame, orient="vertical", command=self.map_canvas.yview)
        y_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.map_canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        
        # Bind events
        self.map_canvas.bind("<Motion>", self.on_mouse_move)
        self.map_canvas.bind("<Button-1>", self.on_mouse_down)
        self.map_canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.map_canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Bind window resize event to update canvas scaling
        self.root.bind("<Configure>", self.on_window_resize)

    def create_spawn_list(self):
        """Create a panel to display and manage current spawns"""
        spawn_frame = ttk.LabelFrame(self.right_panel, text="Mobs on Selected Map")
        spawn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure spawn frame for resizing - POPRAWIONA RESPONSYWNOŚĆ
        spawn_frame.columnconfigure(0, weight=1)
        spawn_frame.rowconfigure(0, weight=0)  # Search ma stałą wysokość
        spawn_frame.rowconfigure(1, weight=0)  # Hide mobs ma stałą wysokość
        spawn_frame.rowconfigure(2, weight=1)  # Lista spawnów rozciąga się
        spawn_frame.rowconfigure(3, weight=0)  # Przyciski mają stałą wysokość
        
        # WYSZUKIWARKA
        search_frame = ttk.Frame(spawn_frame)
        search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=(2, 0))
        search_frame.columnconfigure(1, weight=1)  # Pole wyszukiwania rozciąga się
        
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, sticky=tk.W)
        self.spawn_search_var = tk.StringVar()
        self.spawn_search_var.trace('w', self.update_spawn_list)
        search_entry = ttk.Entry(search_frame, textvariable=self.spawn_search_var, width=30)
        search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Add checkbox to hide mobs
        hide_mobs_frame = ttk.Frame(spawn_frame)
        hide_mobs_frame.grid(row=1, column=0, sticky=(tk.W), padx=5, pady=2)
        self.hide_mobs_var = tk.BooleanVar(value=False)
        hide_mobs_cb = ttk.Checkbutton(hide_mobs_frame, text="Hide Mobs", variable=self.hide_mobs_var, 
                                      command=self.toggle_mobs_visibility)
        hide_mobs_cb.grid(row=0, column=0, sticky=tk.W)
        
        # Create spawn list with scrollbar
        spawn_list_frame = ttk.Frame(spawn_frame)
        spawn_list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure spawn list frame for resizing
        spawn_list_frame.columnconfigure(0, weight=1)
        spawn_list_frame.rowconfigure(0, weight=1)
        
        # Spawn list
        self.spawn_listbox = tk.Listbox(spawn_list_frame, height=10, width=50)
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
        
        # Remove button
        delete_button = ttk.Button(button_frame, text="Remove", command=self.delete_selected_spawn)
        delete_button.grid(row=0, column=0, sticky=(tk.E), padx=5)

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
                                    
                                # Debug output for spiders
                                if "spider" in full_name.lower():
                                    print(f"Spider stats loaded: ID={monster_id}, Name={full_name}, " +
                                          f"AttackType={attack_type}, Attribute={attribute}, FinalType={monster_type}")
                                
                            except (IndexError, ValueError) as e:
                                print(f"Warning: Could not parse monster stats for line: {line.strip()}")
                                continue
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load monster stats: {str(e)}")

    def load_available_maps(self):
        self.map_listbox.delete(0, tk.END)
        
        # Sprawdź czy katalog istnieje, jeśli nie - utwórz go
        if not os.path.exists("MonsterSetBase"):
            try:
                os.makedirs("MonsterSetBase")
                self.status_var.set("Created MonsterSetBase directory")
                messagebox.showinfo("Directory Created", "MonsterSetBase directory was created. Place your map files in this directory.")
                return
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create MonsterSetBase directory: {str(e)}")
                return
        
        # Wczytaj pliki map
        try:
            files = sorted(os.listdir("MonsterSetBase"))
            for file in files:
                if file.endswith(".txt") and not file.startswith("Event"):
                    self.map_listbox.insert(tk.END, file)
            
            if not files:
                self.status_var.set("No map files found in MonsterSetBase directory")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load maps: {str(e)}")

    def load_map_dialog(self):
        # Open file dialog to select map file
        file_path = filedialog.askopenfilename(
            title="Select MonsterSetBase file",
            initialdir="MonsterSetBase",
            filetypes=[("Text Files", "*.txt")]
        )
        if file_path:
            map_file = os.path.basename(file_path)
            self.load_map(map_file)

    def load_map(self, map_file):
        # Clear undo/redo stacks when loading a new map
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.update_undo_redo_states()
        
        try:
            # Load map data
            with open(f"MonsterSetBase/{map_file}", 'r') as f:
                self.spawns = []
                section_type = None
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('//'):
                        continue
                    # Check for section markers
                    if line == "0":
                        section_type = 0  # NPCs
                        continue
                    elif line == "1":
                        section_type = 1  # Monsters/Traps
                        continue
                    elif line.lower() == "end":
                        section_type = None
                        continue
                    parts = line.split()
                    if section_type == 0 and len(parts) >= 6:  # NPC format
                        self.spawns.append({
                            'monster_id': int(parts[0]),
                            'map_number': int(parts[1]),
                            'range': int(parts[2]),
                            'x': int(parts[3]),
                            'y': int(parts[4]),
                            'end_x': int(parts[3]),  # Same as x for NPCs
                            'end_y': int(parts[4]),  # Same as y for NPCs
                            'direction': int(parts[5]),
                            'quantity': 1,  # Always 1 for NPCs
                            'type': 0  # NPC
                        })
                    elif section_type == 1 and len(parts) >= 9:  # Monster format
                        self.spawns.append({
                            'monster_id': int(parts[0]),
                            'map_number': int(parts[1]),
                            'range': int(parts[2]),
                            'x': int(parts[3]),
                            'y': int(parts[4]),
                            'end_x': int(parts[5]),
                            'end_y': int(parts[6]),
                            'direction': int(parts[7]),
                            'quantity': int(parts[8]),
                            'type': 1 if self.monsters.get(int(parts[0]), {}).get('type') == 1 else 2  # Trap or Monster
                        })
                    elif len(parts) >= 6:  # Legacy format
                        monster_id = int(parts[0])
                        monster_type = self.monsters.get(monster_id, {}).get('type', 2)
                        self.spawns.append({
                            'monster_id': monster_id,
                            'map_number': int(parts[1]),
                            'range': int(parts[2]),
                            'x': int(parts[3]),
                            'y': int(parts[4]),
                            'end_x': int(parts[3]),  # Same as x for legacy format
                            'end_y': int(parts[4]),  # Same as y for legacy format
                            'direction': int(parts[5]),
                            'quantity': 1,  # Default for legacy format
                            'type': monster_type
                        })
                    else:
                        print(f"Warning: Skipping malformed line: {line}")
                        # Możesz też dodać ostrzeżenie dla użytkownika:
                        # messagebox.showwarning("Malformed line", f"Skipped line: {line}")
                        
            # Save spawns to memory
            self.map_spawns[map_file] = copy.deepcopy(self.spawns)
            
            # Po wczytaniu mapy automatycznie zaznacz ją na liście
            for idx in range(self.map_listbox.size()):
                if self.map_listbox.get(idx) == map_file:
                    self.map_listbox.selection_clear(0, tk.END)
                    self.map_listbox.selection_set(idx)
                    self.map_listbox.activate(idx)
                    break
            # Load and display map image (lepsze mapowanie)
            try:
                if " - " in map_file:
                    map_name = map_file.split(" - ")[1].split(".")[0]
                else:
                    map_name = os.path.splitext(map_file)[0]
            except Exception:
                map_name = os.path.splitext(map_file)[0]

            image_path = self.find_map_image(map_name)
            expected_file = f"Images/{map_name.strip().replace(' ', '_')}.png"
            if not image_path or not os.path.exists(image_path):
                print(f"Warning: Map image not found for {map_name}")
                # Use default/blank canvas if image missing
                self.original_width = 800
                self.original_height = 600
                
            self.display_map_image(image_path)
            self.display_spawns()
            self.update_spawn_list()  # Update the spawn list
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load map: {str(e)}")
            
    def update_modified_indicator(self):
        """Update the modified indicator in status bar"""
        if hasattr(self, 'modified_var') and hasattr(self, 'selected_map_file'):
            if self.selected_map_file in self.modified_maps:
                self.modified_var.set("Modified*")
            else:
                self.modified_var.set("")

    def find_map_image(self, map_name):
        import os
        
        # Sprawdź czy katalog Images istnieje, jeśli nie - utwórz go
        if not os.path.exists("Images"):
            try:
                os.makedirs("Images")
                self.status_var.set("Created Images directory")
                messagebox.showinfo("Directory Created", "Images directory was created. Place your map images in this directory.")
                return None
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create Images directory: {str(e)}")
                return None
        
        map_exceptions = {
            'Kanturu 1': 'Kanturu_Ruins.png',
            'Kanturu 2': 'Kanturu_Relics.png',
            'Swamp of calmness': 'Swamp_of_Peace.png',
            'Swamp of Calmness': 'Swamp_of_Peace.png',
            '056 - Swamp of Calmness': 'Swamp_of_Peace.png',
        }
        
        # Check explicit mappings first
        if map_name in map_exceptions:
             path = f"Images/{map_exceptions[map_name]}"
             if os.path.exists(path):
                 return path

        # Also check if any key is contained in the map name (partial match)
        for key, val in map_exceptions.items():
            if key in map_name:
                 path = f"Images/{val}"
                 if os.path.exists(path):
                     return path
                     
        base = map_name.strip().replace(" ", "_")
        candidates = [
            f"Images/{base}.png",
            f"Images/{base.lower()}.png",
            f"Images/{base.upper()}.png",
            f"Images/{map_name.strip()}.png",
            f"Images/{map_name.strip().lower()}.png",
            f"Images/{map_name.strip().upper()}.png",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        # Fallback: spróbuj znaleźć plik, który zawiera nazwę mapy (ignorując wielkość liter i podkreślenia)
        try:
            files = os.listdir("Images")
            for f in files:
                if f.lower().endswith(".png") and base.lower() in f.lower():
                    return os.path.join("Images", f)
        except Exception:
            pass
        # Jeśli nie znaleziono, zwróć None
        return None

    def display_map_image(self, image_path):
        self.map_canvas.delete("all")  # Zawsze czyść canvas
        if image_path and os.path.exists(image_path):
            try:
                image = Image.open(image_path)
                self.original_width = image.width
                self.original_height = image.height
                self.original_image = image  # Zachowaj oryginalny obraz
                
                # Pobierz aktualny rozmiar canvas
                canvas_width = self.map_canvas.winfo_width()
                canvas_height = self.map_canvas.winfo_height()
                
                # Jeśli canvas nie ma jeszcze właściwego rozmiaru, użyj domyślnych wartości
                if canvas_width <= 1:
                    canvas_width = 800
                if canvas_height <= 1:
                    canvas_height = 600
                
                # Oblicz skalę, aby obraz zmieścił się w canvas
                scale_x = canvas_width / image.width
                scale_y = canvas_height / image.height
                self.scale = min(scale_x, scale_y)
                
                # Skaluj obraz, jeśli jest za duży dla canvas
                if self.scale < 1:
                    new_width = int(image.width * self.scale)
                    new_height = int(image.height * self.scale)
                    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    self.photo_image = ImageTk.PhotoImage(resized_image)
                    self.map_canvas.create_image(0, 0, image=self.photo_image, anchor="nw")
                    self.map_canvas.configure(scrollregion=(0, 0, new_width, new_height))
                else:
                    # Jeśli obraz jest mniejszy niż canvas, wyświetl bez skalowania
                    self.photo_image = ImageTk.PhotoImage(image)
                    self.map_canvas.create_image(0, 0, image=self.photo_image, anchor="nw")
                    self.map_canvas.configure(scrollregion=(0, 0, image.width, image.height))
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load map image: {str(e)}")
        else:
            # Jeśli nie ma obrazu, utwórz pusty canvas o domyślnych wymiarach
            self.original_width = 800
            self.original_height = 600
            self.scale = 1.0
            self.photo_image = None
            self.original_image = None
            
            self.map_canvas.create_rectangle(0, 0, self.original_width, self.original_height, fill="#222", outline="")
            self.map_canvas.configure(scrollregion=(0, 0, self.original_width, self.original_height))
        
        # Wymuś ponowne bindowanie <Motion> po każdej zmianie mapy
        self.map_canvas.bind("<Motion>", self.on_mouse_move)
        
        # Pokaż spawny na nowej mapie
        self.display_spawns()

    def canvas_to_map_coords(self, canvas_x, canvas_y):
        """Convert canvas coordinates to map coordinates (0-255 range)"""
        # Get current scroll position
        scroll_x = self.map_canvas.xview()[0] * self.original_width
        scroll_y = self.map_canvas.yview()[0] * self.original_height
        
        # Convert canvas coordinates to original image coordinates
        raw_x = (canvas_x / self.scale) + scroll_x
        raw_y = (canvas_y / self.scale) + scroll_y
        
        # Zabezpieczenie przed dzieleniem przez zero
        if not hasattr(self, 'original_width') or self.original_width <= 0:
            return 0, 0
        
        if not hasattr(self, 'original_height') or self.original_height <= 0:
            return 0, 0
        
        # Convert to game coordinates (0-255 range)
        # Używamy wartości zmiennoprzecinkowych dla lepszej precyzji
        map_y_float = (raw_x / self.original_width) * 255.0
        map_x_float = (raw_y / self.original_height) * 255.0
        
        # Stosuj zaokrąglenie matematyczne
        map_y = int(round(map_y_float))
        map_x = int(round(map_x_float))
        
        # Ensure coordinates stay within bounds
        map_x = max(0, min(255, map_x))
        map_y = max(0, min(255, map_y))
        
        return map_x, map_y

    def map_to_canvas_coords(self, map_x, map_y):
        """Convert map coordinates (0-255 range) to canvas coordinates"""
        # Zabezpieczenie przed dzieleniem przez zero
        if not hasattr(self, 'original_width') or self.original_width <= 0:
            return 0, 0
        
        if not hasattr(self, 'original_height') or self.original_height <= 0:
            return 0, 0
        
        # Get current scroll position
        scroll_x = self.map_canvas.xview()[0] * self.original_width
        scroll_y = self.map_canvas.yview()[0] * self.original_height
        
        # Convert from game coordinates (0-255) to image pixel coordinates
        raw_x = (map_y / 255.0) * self.original_width
        raw_y = (map_x / 255.0) * self.original_height
        
        # Apply scale and scroll offset
        canvas_x = (raw_x - scroll_x) * self.scale
        canvas_y = (raw_y - scroll_y) * self.scale
        
        return canvas_x, canvas_y

    def on_mouse_move(self, event):
        map_x, map_y = self.canvas_to_map_coords(event.x, event.y)
        # Update the coordinates in the status bar
        if hasattr(self, 'coordinates_var'):
            self.coordinates_var.set(f"X: {map_x} Y: {map_y}")
        # Remove old coordinate display if it exists
        if self.coord_text:
            self.map_canvas.delete(self.coord_text)
        if self.coord_bg:
            self.map_canvas.delete(self.coord_bg)
        
        # Format text with fixed width for better alignment
        text = f"X: {map_x:3d}  Y: {map_y:3d}"
        
        # Calculate text size (approximation) for better background sizing
        text_width = len(text) * 7  # Approximate width based on characters
        text_height = 20  # Fixed height for text
        
        # Create background rectangle with ample padding
        self.coord_bg = self.map_canvas.create_rectangle(
            event.x + 10, 
            event.y - 30,
            event.x + 10 + text_width + 10,  # Add padding
            event.y - 30 + text_height + 10, # Add padding
            fill="#000066",     # Ciemnogranatowe tło
            outline="#FFFFFF",  # Biała ramka
            width=2,           # Grubsza ramka
            tags="coords"
        )
        
        # Create coordinate text centered on background
        self.coord_text = self.map_canvas.create_text(
            event.x + 15, 
            event.y - 25,
            text=text,
            fill="#FFFFFF",     # Biały tekst
            font=("Arial", 12, "bold"),
            anchor="nw",
            tags="coords"
        )
        
        # Make sure the coordinate display is always on top
        self.map_canvas.tag_raise("coords")
        
        # Zapisz ostatnio wyświetlane współrzędne, aby można było ich użyć później
        self.last_displayed_coords = (map_x, map_y)

    def on_mouse_down(self, event):
        # Usuwaj wszystkie tooltipy przy każdym kliknięciu na mapie
        self.hide_spawn_tooltip(None)
        # Sprawdź, czy kliknięto w istniejącego spawna (nie próbuj dodawać nowego)
        clicked_items = self.map_canvas.find_withtag(tk.CURRENT)
        self.clicked_existing_spawn = False
        if clicked_items:
            tags = self.map_canvas.gettags(clicked_items[0])
            for tag in tags:
                if tag.startswith('spawn_'):
                    # To jest kliknięcie w istniejącego spawna, nie dodawaj nowego
                    self.clicked_existing_spawn = True
                    return
        # Jeśli kliknięto w pobliżu spawna, podświetl go na liście
        nearest_idx = self.find_nearest_spawn(event.x, event.y, max_distance=8)
        if nearest_idx is not None:
            self.select_spawn_in_list(nearest_idx)
            self.clicked_existing_spawn = True
            return
        
        # Zapisz współrzędne kursora dla funkcji dodającej spawn
        self.start_x = self.map_canvas.canvasx(event.x)
        self.start_y = self.map_canvas.canvasy(event.y)
        # Zapisz też aktualne współrzędne mapy wyświetlane w tooltipie
        if hasattr(self, 'last_displayed_coords'):
            self.start_map_coords = self.last_displayed_coords
        else:
            # Jeśli z jakiegoś powodu nie ma zapisanych współrzędnych, oblicz je
            self.start_map_coords = self.canvas_to_map_coords(event.x, event.y)
        
        self.is_selecting = True

    def find_nearest_spawn(self, canvas_x, canvas_y, max_distance=8):
        min_dist = float('inf')
        nearest_idx = None
        for i, spawn in enumerate(self.spawns):
            sx, sy = self.map_to_canvas_coords(spawn['x'], spawn['y'])
            dist = ((canvas_x - sx) ** 2 + (canvas_y - sy) ** 2) ** 0.5
            if dist < min_dist and dist <= max_distance:
                min_dist = dist
                nearest_idx = i
        return nearest_idx

    def on_mouse_drag(self, event):
        if not self.is_selecting:
            return
            
        curr_x = self.map_canvas.canvasx(event.x)
        curr_y = self.map_canvas.canvasy(event.y)
        
        if self.selection_rect:
            self.map_canvas.delete(self.selection_rect)
            
        self.selection_rect = self.map_canvas.create_rectangle(
            self.start_x, self.start_y, curr_x, curr_y,
            outline="blue", dash=(4, 4)
        )

    def on_mouse_up(self, event):
        if hasattr(self, 'clicked_existing_spawn') and self.clicked_existing_spawn:
            self.clicked_existing_spawn = False
            return
        if not self.is_selecting:
            return
        self.is_selecting = False
        end_x = self.map_canvas.canvasx(event.x)
        end_y = self.map_canvas.canvasy(event.y)
        # If it's a small area, treat as single click
        if abs(end_x - self.start_x) < 5 and abs(end_y - self.start_y) < 5:
            self.add_single_spawn(end_x, end_y)
        else:
            self.generate_random_spawns(
                min(self.start_x, end_x), min(self.start_y, end_y),
                max(self.start_x, end_x), max(self.start_y, end_y)
            )
        if self.selection_rect:
            self.map_canvas.delete(self.selection_rect)

    def add_single_spawn(self, canvas_x, canvas_y):
        if not hasattr(self, 'selected_map_file'):
            return  # Nie pokazuj messageboxa, po prostu ignoruj
        if not hasattr(self, 'selected_monster_id'):
            return  # Nie pokazuj messageboxa, po prostu ignoruj
        
        # Użyj dokładnie tych samych współrzędnych, które były wyświetlane w tooltipie
        if hasattr(self, 'start_map_coords'):
            map_x, map_y = self.start_map_coords
        else:
            map_x, map_y = self.canvas_to_map_coords(canvas_x, canvas_y)
        
        self.add_spawn(map_x, map_y)
        print(f"add_single_spawn: Using coords from tooltip: ({map_x}, {map_y})")
        messagebox.showinfo("Info", f"Added spawn at X:{map_x} Y:{map_y}")

    def generate_random_spawns(self, start_x, start_y, end_x, end_y):
        if not hasattr(self, 'selected_map_file'):
            return  # Nie pokazuj messageboxa, po prostu ignoruj
        if not hasattr(self, 'selected_monster_id'):
            return  # Nie pokazuj messageboxa, po prostu ignoruj
        
        # Używaj dokładnie tych współrzędnych, które były pokazywane w tooltipie
        if hasattr(self, 'start_map_coords'):
            start_map_x, start_map_y = self.start_map_coords
        else:
            # Konwertuj współrzędne canvas do współrzędnych mapy
            start_map_x, start_map_y = self.canvas_to_map_coords(start_x, start_y)
        
        # Dla end_x, end_y również używaj aktualnych współrzędnych z podglądu
        if hasattr(self, 'last_displayed_coords'):
            end_map_x, end_map_y = self.last_displayed_coords
        else:
            end_map_x, end_map_y = self.canvas_to_map_coords(end_x, end_y)
        
        monster_id = self.selected_monster_id
        # Check if it's an NPC
        if self.monsters[monster_id]['type'] == 0:
            center_x = (start_map_x + end_map_x) // 2
            center_y = (start_map_y + end_map_y) // 2
            self.add_spawn(center_x, center_y)
            print(f"generate_random_spawns (NPC): ({center_x}, {center_y})")
            messagebox.showinfo("Info", f"Added NPC at X:{center_x} Y:{center_y}")
        else:
            self.add_spawn(
                min(start_map_x, end_map_x), 
                min(start_map_y, end_map_y),
                max(start_map_x, end_map_x),
                max(start_map_y, end_map_y)
            )
            print(f"generate_random_spawns (area): ({min(start_map_x, end_map_x)}, {min(start_map_y, end_map_y)}) to ({max(start_map_x, end_map_x)}, {max(start_map_y, end_map_y)})")
            messagebox.showinfo("Info", f"Added spawn area: X:{min(start_map_x, end_map_x)}-{max(start_map_x, end_map_x)} Y:{min(start_map_y, end_map_y)}-{max(start_map_y, end_map_y)}")

    def add_spawn(self, x, y, end_x=None, end_y=None):
        # Save current state before adding
        self.save_state("Add Spawn")
        
        # Używaj zapamiętanych wyborów
        monster_id = getattr(self, 'selected_monster_id', None)
        map_file = getattr(self, 'selected_map_file', None)
        if monster_id is None or map_file is None:
            messagebox.showwarning("Warning", "Please select a map and a monster first.")
            return
        monster_type = self.monsters[monster_id]['type']
        if end_x is None:
            end_x = x
        if end_y is None:
            end_y = y
        quantity = 1
        if monster_type != 0:
            quantity = self.quantity_var.get()
        direction = self.direction_var.get()
        # Pobierz numer mapy z nazwy pliku
        try:
            map_number = int(map_file.split(" - ")[0])
        except Exception:
            map_number = 0
        spawn = {
            'monster_id': monster_id,
            'map_number': map_number,
            'range': self.range_var.get(),
            'x': x,
            'y': y,
            'end_x': end_x,
            'end_y': end_y,
            'direction': direction,
            'quantity': quantity,
            'type': monster_type
        }
        self.spawns.append(spawn)
        self.display_spawns()
        self.update_spawn_list()
        
        # Mark map as modified
        if hasattr(self, 'selected_map_file'):
            self.modified_maps.add(self.selected_map_file)
            self.update_modified_indicator()

    def display_spawns(self):
        """Display all spawns on the map unless hide_mobs is checked"""
        self.map_canvas.delete("spawn")
        if self.coord_text:
            self.map_canvas.delete(self.coord_text)
        if self.coord_bg:
            self.map_canvas.delete(self.coord_bg)
        # If hide_mobs is checked, don't display any spawns
        if hasattr(self, 'hide_mobs_var') and self.hide_mobs_var.get():
            return
        selected_spawn = None
        if hasattr(self, 'selected_spawn_index') and self.selected_spawn_index >= 0:
            selected_spawn = self.spawns[self.selected_spawn_index]
        if self.monster_listbox.curselection():
            monster_text = self.monster_listbox.get(self.monster_listbox.curselection())
            if not monster_text.startswith("==="):
                selected_monster_id = int(monster_text.split(":")[0])
        
        # Pre-calculate counts per coordinate to show stacked mobs
        coord_counts = {}
        for s in self.spawns:
            k = (s['x'], s['y'])
            coord_counts[k] = coord_counts.get(k, 0) + 1

        for i, spawn in enumerate(self.spawns):
            # Convert map coordinates to canvas coordinates
            canvas_x, canvas_y = self.map_to_canvas_coords(spawn['x'], spawn['y'])
            is_selected = (i == self.selected_spawn_index if hasattr(self, 'selected_spawn_index') else False)
            is_same_monster = False
            if hasattr(self, 'selected_monster_id'):
                is_same_monster = spawn['monster_id'] == self.selected_monster_id
            # Draw spawn point with color based on mob type
            color = "red"  # Default for standard monsters (type 2)
            if spawn['type'] == 0:  # NPC
                color = "yellow"
            elif spawn['type'] == 1:  # Multiple 
                color = "blue"
            elif spawn['type'] == 3:  # Multiple (green)
                color = "green"
            elif spawn['type'] == 4:  # Event
                color = "cyan"
            
            # HIGHLIGHT LOGIC:
            # Only the specifically selected spawn gets the big highlight.
            # Same monster types are not highlighted to avoid confusion.
            radius = 6 if is_selected else 4
            outline_color = "white" if is_selected else "black"
            
            tag = f"spawn_{i}"
            self.map_canvas.create_oval(
                canvas_x-radius, canvas_y-radius,
                canvas_x+radius, canvas_y+radius,
                fill=color, outline=outline_color, width=2,
                tags=("spawn", tag, f"monster_{spawn['monster_id']}")
            )
            # For monsters and traps with area, draw rectangle
            if spawn['type'] != 0 and (spawn['x'] != spawn['end_x'] or spawn['y'] != spawn['end_y']):
                canvas_end_x, canvas_end_y = self.map_to_canvas_coords(spawn['end_x'], spawn['end_y'])
                self.map_canvas.create_rectangle(
                    canvas_x, canvas_y, canvas_end_x, canvas_end_y,
                    outline=color, dash=(2, 2), width=1,
                    tags=("spawn", tag, f"monster_{spawn['monster_id']}")
                )
            # Add tooltip with monster info
            monster_name = self.monsters.get(spawn['monster_id'], {}).get('name', "Unknown")
            
            # Add stack count to tooltip if multiple mobs are here
            stack_count = coord_counts.get((spawn['x'], spawn['y']), 1)
            if stack_count > 1:
                monster_name += f" (Stacked: {stack_count})"
            
            self.map_canvas.tag_bind(
                tag, 
                "<Enter>", 
                lambda e, s=spawn, n=monster_name: self.show_spawn_tooltip(e, s, n)
            )
            self.map_canvas.tag_bind(
                tag, 
                "<Leave>", 
                self.hide_spawn_tooltip
            )
            # Now bind click on this spawn to select it in the list
            self.map_canvas.tag_bind(tag, "<Button-1>", lambda event, idx=i: self.select_spawn_in_list(idx))

        # Draw stack counts on visualization layer
        for (mx, my), count in coord_counts.items():
            if count > 1:
                cx, cy = self.map_to_canvas_coords(mx, my)
                # Draw a small text indicating the count above the dot
                self.map_canvas.create_text(
                    cx, cy - 8, 
                    text=f"x{count}",
                    fill="white",
                    font=("Segoe UI", 8, "bold"),
                    tags="spawn"
                )

        # Only raise the SELECTED spawn to the top, so it catches events over overlapping ones
        if hasattr(self, 'selected_spawn_index') and self.selected_spawn_index >= 0:
             tag = f"spawn_{self.selected_spawn_index}"
             self.map_canvas.tag_raise(tag)

    def select_spawn_in_list(self, idx):
        # Load data to UI immediately
        self.load_spawn_to_ui(idx)
        
        # Now try to select in listbox
        self.spawn_listbox.selection_clear(0, tk.END)
        
        # Construct the text we expect to find
        spawn = self.spawns[idx]
        monster_name = self.monsters.get(spawn['monster_id'], {}).get('name', "Unknown")
        target_text = ""
        
        if spawn['type'] == 0:  # NPC
            target_text = f"({spawn['x']}, {spawn['y']}) 🧍 {monster_name}"
        else:  # Monster or Trap
            type_icon = "⚠️" if spawn['type'] == 1 else "👹"
            target_text = f"({spawn['x']}, {spawn['y']}) {type_icon} {monster_name} - Qty: {spawn['quantity']} - Area: ({spawn['x']}, {spawn['y']}) to ({spawn['end_x']}, {spawn['end_y']})"
            
        # Search for this text in listbox
        found_idx = -1
        list_size = self.spawn_listbox.size()
        for i in range(list_size):
            if self.spawn_listbox.get(i) == target_text:
                found_idx = i
                break
                
        if found_idx >= 0:
            self.spawn_listbox.selection_set(found_idx)
            self.spawn_listbox.activate(found_idx)
            self.spawn_listbox.see(found_idx)

    def show_spawn_tooltip(self, event, spawn, monster_name):
        """Show tooltip with monster information when hovering over a spawn point"""
        self.hide_spawn_tooltip(None)  # Zawsze chowaj poprzedni tooltip
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        self.tooltip = tk.Toplevel()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x+10}+{y+10}")
        # Format based on monster type
        if spawn['type'] == 0:  # NPC
            label = tk.Label(self.tooltip, 
                          text=f"{monster_name} (NPC)\nID: {spawn['monster_id']}\nPos: ({spawn['x']}, {spawn['y']}) [0-255]",
                          justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        else:  # Monster or Trap
            type_name = "Trap" if spawn['type'] == 1 else "Monster"
            label = tk.Label(self.tooltip, 
                          text=(f"{monster_name} ({type_name})\nID: {spawn['monster_id']}\n"
                               f"Range: {spawn['range']}\nQuantity: {spawn['quantity']}\n"
                               f"Area: ({spawn['x']}, {spawn['y']}) - ({spawn['end_x']}, {spawn['end_y']}) [0-255]"),
                          justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack()

    def hide_spawn_tooltip(self, event):
        """Hide the tooltip window"""
        if hasattr(self, 'tooltip') and self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def on_monster_selected(self, event):
        selection = self.monster_listbox.curselection()
        if selection:
            monster_text = self.monster_listbox.get(selection[0])
            if monster_text.startswith("==="):
                return
            
            # Extract monster ID from the text (format: "123: 🧍 Monster Name")
            try:
                monster_id = int(monster_text.split(":")[0])
                self.selected_monster_id = monster_id
                
                # Get the monster type directly from Monster.txt/monster_stats
                if monster_id in self.monster_stats:
                    stats = self.monster_stats[monster_id]
                    
                    # Get attack type and attribute to determine correct monster type
                    attack_type = stats.get('attacktype', -1)
                    attribute = stats.get('attribute', -1)
                    
                    # Determine monster type based on attribute
                    # 0 = NPC, 1 = Trap, 2 = Monster
                    monster_type = attribute
                    
                    # Ensure type is correctly recorded in both dictionaries
                    if monster_id in self.monster_stats:
                        self.monster_stats[monster_id]['type'] = monster_type
                    
                    if monster_id in self.monsters:
                        self.monsters[monster_id]['type'] = monster_type
                    
                    # Debug output with attribute number
                    # print(f"Selected monster: ID={monster_id}, Name={stats.get('name', 'Unknown')}, " +
                    #      f"AttackType={attack_type}, Attribute={attribute}, FinalType={monster_type}")
                    
                    # Update all form fields with the correct monster stats
                    for key, var in self.stat_vars.items():
                        if key in stats:
                            var.set(str(stats[key]))
                        else:
                            var.set("0")  # Default value
                    
                    # Set direction if available
                    if hasattr(self, 'direction_var'):
                        self.direction_var.set(stats.get('direction', -1))
                    
                    # Set mob type if available
                    if hasattr(self, 'mob_type_var'):
                        self.mob_type_var.set(monster_type)
                
                # Update quantity field based on monster type
                if hasattr(self, 'quantity_spinbox'):
                    if monster_type == 0:  # NPC
                        self.quantity_spinbox.configure(state='disabled')
                        self.quantity_var.set(1)
                    else:
                        self.quantity_spinbox.configure(state='normal')
                
                # Refresh display to highlight selected monster spawns
                self.display_spawns()
            except (ValueError, IndexError) as e:
                print(f"Error parsing monster selection: {e}")
                messagebox.showerror("Error", f"Failed to select monster: {str(e)}")

    def filter_monsters(self, *args):
        self.update_monster_list()

    def update_monster_list(self):
        """Update the monster list based on search text"""
        self.monster_listbox.delete(0, tk.END)
        search_text = self.search_var.get().lower()
        
        # Create lists for different monster types
        npcs = []
        monsters = []
        
        # Populate lists based on monster types from monster_stats
        for monster_id, monster_data in self.monsters.items():
            # Get initial type from monster data
            monster_type = monster_data.get('type', 2)  # Default to monster (2)
            
            # Update from more accurate data in monster_stats
            if hasattr(self, 'monster_stats') and monster_id in self.monster_stats:
                monster_type = self.monster_stats[monster_id]['type']
                monster_data['type'] = monster_type  # Update main record
            
            # Debug for spiders
            if "spider" in monster_data['name'].lower():
                print(f"Spider in update_monster_list: ID={monster_id}, Name={monster_data['name']}, Type={monster_type}")
            
            # Filter based on search text
            if search_text in monster_data['name'].lower() or search_text in str(monster_id):
                if monster_type == 0:  # NPCs have attacktype = 0
                    npcs.append((monster_id, monster_data['name']))
                else:  # All others are monsters (type 2, 3, 4)
                    monsters.append((monster_id, monster_data['name']))
        
        # Add NPCs section
        if npcs:
            self.monster_listbox.insert(tk.END, "=== NPCs ===")
            # Sort by ID
            for monster_id, name in sorted(npcs, key=lambda x: x[0]):
                self.monster_listbox.insert(tk.END, f"{monster_id}: 🧍 {name}")
        
        # Add Monsters section
        if monsters:
            self.monster_listbox.insert(tk.END, "=== Monsters ===")
            # Sort by ID
            for monster_id, name in sorted(monsters, key=lambda x: x[0]):
                # Get the specific monster type for precise icon
                monster_type = self.monsters[monster_id]['type']
                type_symbol = "👹"  # Default monster icon
                if monster_type == 3:
                    type_symbol = "🟢"  # Green multiple
                elif monster_type == 4:
                    type_symbol = "🔵"  # Event
                self.monster_listbox.insert(tk.END, f"{monster_id}: {type_symbol} {name}")
                
        # Print debug info
        print(f"Monster list updated with search: '{search_text}', found {len(npcs)} NPCs, {len(monsters)} monsters")

    def save_changes(self):
        map_file = getattr(self, 'selected_map_file', None)
        if not map_file:
            messagebox.showwarning("Warning", "Please select a map first")
            return
        try:
            filename = f"MonsterSetBase/{map_file}"
            # Show info about filename format
            messagebox.showinfo(
                "Filename Reminder",
                "Remember: The file name should be in the format '007 - Atlans.txt' (map number, dash, map name).\nSaving with a wrong name may cause issues in the game."
            )
            # Group spawns by type
            npcs = [s for s in self.spawns if s['type'] == 0]
            monsters = [s for s in self.spawns if s['type'] != 0]
            with open(filename, 'w') as f:
                # Write header
                f.write("//=========================================================================================================================================" + "\n")
                f.write("// NPCS\n")
                f.write("//=========================================================================================================================================" + "\n")
                f.write("0\n")
                f.write("//Monster      MapNumber      Range      PositionX      PositionY      Direction      Comment\n")
                # Write NPCs
                for spawn in npcs:
                    monster_name = self.monsters.get(spawn['monster_id'], {}).get('name', "Unknown")
                    f.write(f"{spawn['monster_id']:<14}{spawn['map_number']:<14}{spawn['range']:<12}"
                           f"{spawn['x']:<14}{spawn['y']:<14}{spawn['direction']:<14}//{monster_name}\n")
                f.write("end\n\n")
                # Write monsters section header
                f.write("//=========================================================================================================================================" + "\n")
                f.write("// MONSTERS\n")
                f.write("//=========================================================================================================================================" + "\n")
                f.write("1\n")
                f.write("//Monster      MapNumber      Range      BeginPosX      BeginPosY      EndPosX      EndPosY      Direction      Quantity      Comment\n")
                # Write monsters
                for spawn in monsters:
                    monster_name = self.monsters.get(spawn['monster_id'], {}).get('name', "Unknown")
                    f.write(f"{spawn['monster_id']:<14}{spawn['map_number']:<14}{spawn['range']:<12}"
                           f"{spawn['x']:<14}{spawn['y']:<14}{spawn['end_x']:<14}{spawn['end_y']:<14}"
                           f"{spawn['direction']:<14}{spawn['quantity']:<14}//{monster_name}\n")
                f.write("end\n")
                
            # Remove from modified maps list after saving
            if map_file in self.modified_maps:
                self.modified_maps.remove(map_file)
                self.update_modified_indicator()
                
            messagebox.showinfo("Success", "Changes saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save changes: {str(e)}")

    def on_map_selected(self, event):
        selection = self.map_listbox.curselection()
        if selection:
            map_file = self.map_listbox.get(selection[0])
            # Nie ładuj ponownie tej samej mapy
            if hasattr(self, 'selected_map_file') and self.selected_map_file == map_file:
                return
                
            # Check if current map has unsaved changes and save them to memory
            if hasattr(self, 'selected_map_file') and self.selected_map_file:
                self.save_map_to_memory(self.selected_map_file)
                
            self.selected_map_file = map_file
            
            # Check if we already have spawns for this map in memory
            if map_file in self.map_spawns:
                # Load from memory
                print(f"Loading map {map_file} from memory")
                self.spawns = copy.deepcopy(self.map_spawns[map_file])
                
                # Clear undo/redo stacks when switching maps
                self.undo_stack = []
                self.redo_stack = []
                self.update_undo_redo_states()
                
                # Load map image and display spawns
                try:
                    if " - " in map_file:
                        map_name = map_file.split(" - ")[1].split(".")[0]
                    else:
                        map_name = os.path.splitext(map_file)[0]
                except Exception:
                    map_name = map_file

                image_path = self.find_map_image(map_name)
                self.display_map_image(image_path)
                self.display_spawns()
                self.update_spawn_list()
                
                # Update status bar
                if map_file in self.modified_maps:
                    self.status_var.set(f"Loaded modified map: {map_file}")
                else:
                    self.status_var.set(f"Loaded map: {map_file}")
            else:
                # Load from file
                self.load_map(map_file)
                
            # Update modified indicator
            self.update_modified_indicator()

    def update_spawn_list(self, *args):
        """Update the spawn list with current spawns, with search filter"""
        self.spawn_listbox.delete(0, tk.END)
        search_text = self.spawn_search_var.get().lower() if hasattr(self, 'spawn_search_var') else ""
        # Group spawns by type
        npcs = [s for s in self.spawns if s['type'] == 0]
        monsters = [s for s in self.spawns if s['type'] != 0]

        # Sort monsters by coordinate X, Y for better grouping
        npcs.sort(key=lambda s: (s['x'], s['y']))
        monsters.sort(key=lambda s: (s['x'], s['y']))

        # Add NPCs section
        if npcs:
            self.spawn_listbox.insert(tk.END, "=== NPCs ===")
            for spawn in npcs:
                monster_name = self.monsters.get(spawn['monster_id'], {}).get('name', "Unknown")
                entry = f"({spawn['x']}, {spawn['y']}) 🧍 {monster_name}"
                if (not search_text or
                    search_text in monster_name.lower() or
                    search_text in str(spawn['monster_id']) or
                    search_text in "npc"):
                    self.spawn_listbox.insert(tk.END, entry)
        # Add Monsters/Traps section
        if monsters:
            self.spawn_listbox.insert(tk.END, "=== Monsters & Traps ===")
            for spawn in monsters:
                monster_name = self.monsters.get(spawn['monster_id'], {}).get('name', "Unknown")
                type_icon = "⚠️" if spawn['type'] == 1 else "👹"
                entry = f"({spawn['x']}, {spawn['y']}) {type_icon} {monster_name} - Qty: {spawn['quantity']} - Area: ({spawn['x']}, {spawn['y']}) to ({spawn['end_x']}, {spawn['end_y']})"
                if (not search_text or
                    search_text in monster_name.lower() or
                    search_text in str(spawn['monster_id']) or
                    (spawn['type'] == 1 and "trap" in search_text) or
                    (spawn['type'] != 1 and "monster" in search_text)):
                    self.spawn_listbox.insert(tk.END, entry)



    def delete_selected_spawn(self):
        """Delete the currently selected spawn"""
        if hasattr(self, 'selected_spawn_index') and self.selected_spawn_index >= 0:
            # Save current state before deleting
            self.save_state("Remove Spawn")
            
            # Remove the spawn
            del self.spawns[self.selected_spawn_index]
            self.selected_spawn_index = -1
            
            # Update the display
            self.update_spawn_list()
            self.display_spawns()
            
            # Mark map as modified
            if hasattr(self, 'selected_map_file'):
                self.modified_maps.add(self.selected_map_file)
                self.update_modified_indicator()

    def toggle_mobs_visibility(self):
        """Toggle the visibility of mobs on the map"""
        self.display_spawns()

    def update_monster_stats(self):
        """Update the monster stats based on the UI values"""
        if not hasattr(self, 'selected_monster_id'):
            messagebox.showwarning("Warning", "No monster selected to update")
            return
            
        # Collect all values from the UI
        monster_id = self.selected_monster_id
        updated_stats = {}
        
        for key, var in self.stat_vars.items():
            if key != "name":  # Handle name separately
                try:
                    value = int(var.get()) if var.get() else 0
                    updated_stats[key] = value
                except ValueError:
                    messagebox.showwarning("Warning", f"Invalid value for {key}: {var.get()}")
                    return
            else:
                updated_stats[key] = var.get()
        
        # Update the monster stats in memory
        self.monster_stats[monster_id] = updated_stats
        self.monster_stats[monster_id]['id'] = monster_id
        
        # Update the monster name in the monster list
        self.monsters[monster_id]['name'] = updated_stats['name']
        
        # Update the monster type
        monster_type = self.mob_type_var.get()
        self.monsters[monster_id]['type'] = monster_type
        self.monster_stats[monster_id]['type'] = monster_type
        
        # Refresh the monster list and spawns
        self.update_monster_list()
        self.display_spawns()
        messagebox.showinfo("Success", f"Monster {monster_id} updated successfully")

    def update_direction_label(self):
        value = self.direction_var.get()
        self.direction_label_var.set(f"Selected direction: {value}")

    def show_instructions(self):
        instructions = """
Monster & MonsterSetBase Editor - Instructions

1. Select a map from the Map Selection panel
2. Choose a monster from the monster list
3. Click or drag on the map to add spawns:
   - Single click: Add a single mob
   - Drag area: Create a spawn area with multiple mobs
4. Use the quantity and range fields to control spawn properties
5. Select a direction using the direction control
6. Edit monster stats if needed
7. Save your changes using File > Save

Tips:
- Use the search field to find specific monsters
- Click on existing spawns to select them
- Use the Remove button to delete selected spawns
- Toggle "Hide Mobs" to see the map without spawns
        """
        messagebox.showinfo("Instructions", instructions)
        
    def show_about(self):
        about_text = """
Monster & MonsterSetBase Editor
Version: 1.1
Dedicated for Season 6 files by Louis

Created by Shizoo
Modifications by Popoman
A visual editor for MU Online monster spawn files.
        """
        messagebox.showinfo("About", about_text)

    def load_spawn_to_ui(self, spawn_index):
        """Load spawn data into the UI editor panels"""
        if spawn_index < 0 or spawn_index >= len(self.spawns):
            return

        self.selected_spawn_index = spawn_index
        spawn = self.spawns[spawn_index]
        monster_id = spawn['monster_id']

        # Aktualizuj pola koordynatów
        self.spawn_x_var.set(spawn['x'])
        self.spawn_y_var.set(spawn['y'])
        self.spawn_end_x_var.set(spawn['end_x'])
        self.spawn_end_y_var.set(spawn['end_y'])

        # Aktualizuj inne pola, jeśli są dostępne w interfejsie
        if hasattr(self, 'direction_var'):
            self.direction_var.set(spawn['direction'])
            self.update_direction_label()

        if hasattr(self, 'quantity_var'):
            self.quantity_var.set(spawn['quantity'])

        if hasattr(self, 'spawn_qty_var'):
            if spawn['type'] != 0:
                self.spawn_qty_var.set(spawn['quantity'])
            else:
                self.spawn_qty_var.set(1)

        if hasattr(self, 'spawn_range_var'):
            self.spawn_range_var.set(spawn['range'])

        if hasattr(self, 'mob_type_var'):
            self.mob_type_var.set(spawn['type'])

        # Pokaż ramkę z koordynatami
        if hasattr(self, 'spawn_coords_frame'):
            self.spawn_coords_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
            self.spawn_coords_frame.master.update_idletasks()

        # Załaduj również statystyki moba, jeśli dostępne
        if monster_id in self.monster_stats:
            monster_data = self.monster_stats[monster_id]
            for key, var in self.stat_vars.items():
                if key in monster_data:
                    var.set(str(monster_data[key]))
        else:
             # Jeśli brak statystyk, spróbuj chociaż wyświetlić podstawowe dane
            if 'name' in self.stat_vars:
                self.stat_vars['name'].set(self.monsters.get(monster_id, {}).get('name', 'Unknown'))
            if 'id' in self.stat_vars:
                self.stat_vars['id'].set(str(monster_id))
        
        # Wymuś odświeżenie widoku ramki
        if hasattr(self, 'spawn_coords_frame'):
            self.spawn_coords_frame.update_idletasks()
            
        # Aktualizuj selected_monster_id
        self.selected_monster_id = monster_id
        
        # Odśwież widok mapy (aby zaktualizować zaznaczenie)
        self.display_spawns()

    def update_selected_spawn(self):
        """Update the properties of the selected spawn"""
        if not hasattr(self, 'selected_spawn_index') or self.selected_spawn_index < 0:
            messagebox.showwarning("Warning", "No spawn selected to update")
            return
            
        try:
            # Save current state before updating
            self.save_state("Update Spawn")
            
            # Pobierz wartości z pól
            x = self.spawn_x_var.get()
            y = self.spawn_y_var.get()
            end_x = self.spawn_end_x_var.get()
            end_y = self.spawn_end_y_var.get()
            
            # Sprawdź poprawność wartości
            if not (0 <= x <= 255 and 0 <= y <= 255 and 0 <= end_x <= 255 and 0 <= end_y <= 255):
                messagebox.showwarning("Warning", "Coordinates must be between 0 and 255")
                return
                
            # Aktualizuj spawn
            self.spawns[self.selected_spawn_index]['x'] = x
            self.spawns[self.selected_spawn_index]['y'] = y
            self.spawns[self.selected_spawn_index]['end_x'] = end_x
            self.spawns[self.selected_spawn_index]['end_y'] = end_y
            
            # Dla NPCs end_x i end_y powinny być równe x i y
            if self.spawns[self.selected_spawn_index]['type'] == 0:
                self.spawns[self.selected_spawn_index]['end_x'] = x
                self.spawns[self.selected_spawn_index]['end_y'] = y
            
            # Zaktualizuj kierunek i ilość jeśli są dostępne w interfejsie
            if hasattr(self, 'direction_var'):
                self.spawns[self.selected_spawn_index]['direction'] = self.direction_var.get()
                
            if hasattr(self, 'spawn_qty_var') and self.spawns[self.selected_spawn_index]['type'] != 0:
                self.spawns[self.selected_spawn_index]['quantity'] = self.spawn_qty_var.get()
            
            if hasattr(self, 'spawn_range_var'):
                self.spawns[self.selected_spawn_index]['range'] = self.spawn_range_var.get()
                
            # Odśwież listę i wyświetlanie
            self.update_spawn_list()
            self.display_spawns()
            
            # Mark map as modified
            if hasattr(self, 'selected_map_file'):
                self.modified_maps.add(self.selected_map_file)
                self.update_modified_indicator()
                
            messagebox.showinfo("Success", f"Spawn updated successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update spawn: {str(e)}")

    def on_spawn_selected(self, event):
        """Handle spawn selection in the list"""
        selection = self.spawn_listbox.curselection()
        if not selection:
            return
            
        selected_text = self.spawn_listbox.get(selection[0])
        if selected_text.startswith("==="):
            return
            
        # Find the corresponding spawn
        spawn_index = -1
        for i, spawn in enumerate(self.spawns):
            monster_name = self.monsters.get(spawn['monster_id'], {}).get('name', "Unknown")
            
            if spawn['type'] == 0:  # NPC
                if f"({spawn['x']}, {spawn['y']}) 🧍 {monster_name}" == selected_text:
                    spawn_index = i
                    break
            else:  # Monster or Trap
                type_icon = "⚠️" if spawn['type'] == 1 else "👹"
                if f"({spawn['x']}, {spawn['y']}) {type_icon} {monster_name} - Qty: {spawn['quantity']} - Area: ({spawn['x']}, {spawn['y']}) to ({spawn['end_x']}, {spawn['end_y']})" == selected_text:
                    spawn_index = i
                    break
        
        if spawn_index >= 0:
            self.load_spawn_to_ui(spawn_index)

    def on_window_resize(self, event):
        """Handle window resize to update map scaling"""
        # Ignore events from other widgets
        if event.widget == self.root:
            # Only update if we have a map loaded
            if hasattr(self, 'original_image') and self.original_image:
                self.update_map_scale()

    def update_map_scale(self):
        """Update map scale based on current canvas size"""
        if not hasattr(self, 'original_image') or not self.original_image:
            return
            
        # Get current canvas dimensions
        canvas_width = self.map_canvas.winfo_width()
        canvas_height = self.map_canvas.winfo_height()
        
        # Skip if canvas size not yet properly initialized
        if canvas_width <= 1 or canvas_height <= 1:
            return
            
        # Calculate new scale
        scale_x = canvas_width / self.original_width
        scale_y = canvas_height / self.original_height
        self.scale = min(scale_x, scale_y)
        
        # Resize image if needed
        # We generally want to fit the image in the canvas, maintaining aspect ratio
        new_width = int(self.original_width * self.scale)
        new_height = int(self.original_height * self.scale)
        
        if new_width > 0 and new_height > 0:
             try:
                if self.scale != 1.0: # Only resize if we need to
                    resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    self.photo_image = ImageTk.PhotoImage(resized_image)
                else:
                    self.photo_image = ImageTk.PhotoImage(self.original_image)
                    
                self.map_canvas.delete("all")
                self.map_canvas.create_image(0, 0, image=self.photo_image, anchor="nw")
                self.map_canvas.configure(scrollregion=(0, 0, new_width, new_height))
                
                # Redisplay spawns with updated scale
                self.display_spawns()
             except Exception as e:
                pass # Suppress image scaling errors during resize flood

    def toggle_mobs_visibility_menu(self):
        """Toggle visibility of mobs from menu"""
        self.hide_mobs_var.set(not self.view_mobs_var.get())
        self.toggle_mobs_visibility()

    def zoom_in(self):
        """Increase map zoom by 20%"""
        if hasattr(self, 'scale') and self.scale > 0:
            self.scale = min(self.scale * 1.2, 5.0)  # Limit zoom in to 500%
            self.update_scale_display()
            self.update_map_with_scale()

    def zoom_out(self):
        """Decrease map zoom by 20%"""
        if hasattr(self, 'scale') and self.scale > 0:
            self.scale = max(self.scale * 0.8, 0.1)  # Limit zoom out to 10%
            self.update_scale_display()
            self.update_map_with_scale()

    def reset_zoom(self):
        """Reset zoom to 100%"""
        if hasattr(self, 'scale'):
            self.scale = 1.0
            self.update_scale_display()
            self.update_map_with_scale()

    def update_scale_display(self):
        """Update scale indicator in status bar"""
        if hasattr(self, 'scale_var'):
            scale_percent = int(self.scale * 100)
            self.scale_var.set(f"Scale: {scale_percent}%")

    def update_map_with_scale(self):
        """Update map display with current scale"""
        if not hasattr(self, 'original_image') or not self.original_image:
            return
            
        self.map_canvas.delete("all")
        
        # Resize image based on scale
        new_width = int(self.original_width * self.scale)
        new_height = int(self.original_height * self.scale)
        
        if new_width > 0 and new_height > 0:
            try:
                resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.photo_image = ImageTk.PhotoImage(resized_image)
                self.map_canvas.create_image(0, 0, image=self.photo_image, anchor="nw")
                self.map_canvas.configure(scrollregion=(0, 0, new_width, new_height))
                
                # Wyświetl spawny z nową skalą
                self.display_spawns()
            except Exception as e:
                print(f"Error scaling image: {e}")

    # Add these new methods for undo/redo functionality
    def save_state(self, action_name):
        """Save current state to undo stack"""
        print(f"Saving state: {action_name}")  # Debug
        
        # Create a copy of current spawns for the undo stack
        current_state = {
            'spawns': copy.deepcopy(self.spawns),
            'action': action_name,
            'selected_spawn_index': getattr(self, 'selected_spawn_index', -1)
        }
        
        # Add to undo stack and clear redo stack (since we're creating a new action path)
        self.undo_stack.append(current_state)
        self.redo_stack.clear()
        
        # Limit the size of the undo stack
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        
        # Update menu states
        self.update_undo_redo_states()
        
        # Update status bar
        self.status_var.set(f"Action: {action_name}")
        
        # Mark map as modified
        if hasattr(self, 'selected_map_file'):
            self.modified_maps.add(self.selected_map_file)
            self.update_modified_indicator()

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

    def undo(self):
        """Restore the previous state from undo stack"""
        print("Undo called")  # Debug
        if not self.undo_stack:
            print("Undo stack empty")  # Debug
            return
        
        # Get the current state for the redo stack
        current_state = {
            'spawns': copy.deepcopy(self.spawns),
            'action': self.undo_stack[-1]['action'],
            'selected_spawn_index': getattr(self, 'selected_spawn_index', -1)
        }
        self.redo_stack.append(current_state)
        
        # Restore the previous state
        previous_state = self.undo_stack.pop()
        self.spawns = previous_state['spawns']
        if 'selected_spawn_index' in previous_state:
            self.selected_spawn_index = previous_state['selected_spawn_index']
        
        # Update display
        self.display_spawns()
        self.update_spawn_list()
        
        # Update menu states
        self.update_undo_redo_states()
        
        # Update status bar
        self.status_var.set(f"Undid: {previous_state['action']}")
        print(f"Undid: {previous_state['action']}")  # Debug

    def redo(self):
        """Restore the next state from redo stack"""
        print("Redo called")  # Debug
        if not self.redo_stack:
            print("Redo stack empty")  # Debug
            return
        
        # Get the current state for the undo stack
        current_state = {
            'spawns': copy.deepcopy(self.spawns),
            'action': self.redo_stack[-1]['action'],
            'selected_spawn_index': getattr(self, 'selected_spawn_index', -1)
        }
        self.undo_stack.append(current_state)
        
        # Restore the next state
        next_state = self.redo_stack.pop()
        self.spawns = next_state['spawns']
        if 'selected_spawn_index' in next_state:
            self.selected_spawn_index = next_state['selected_spawn_index']
        
        # Update display
        self.display_spawns()
        self.update_spawn_list()
        
        # Update menu states
        self.update_undo_redo_states()
        
        # Update status bar
        self.status_var.set(f"Redid: {next_state['action']}")
        print(f"Redid: {next_state['action']}")  # Debug

    def save_map_to_memory(self, map_file):
        """Save current map spawns to memory"""
        if hasattr(self, 'spawns') and self.spawns:
            self.map_spawns[map_file] = copy.deepcopy(self.spawns)
            print(f"Saved map {map_file} to memory with {len(self.spawns)} spawns")
            
            # Mark as modified if there are unsaved changes
            if hasattr(self, 'undo_stack') and self.undo_stack:
                self.modified_maps.add(map_file)

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
            elif result:  # Yes, save changes
                # Save current map first
                if hasattr(self, 'selected_map_file') and self.selected_map_file in self.modified_maps:
                    self.save_changes()
                
                # Prompt for saving other modified maps
                for map_file in sorted(self.modified_maps.copy()):  # Use copy to avoid modification during iteration
                    if not hasattr(self, 'selected_map_file') or map_file != self.selected_map_file:
                        save_this = messagebox.askyesno(
                            "Save Map",
                            f"Save changes to {map_file}?",
                            icon="question"
                        )
                        if save_this:
                            # Switch to this map temporarily and save it
                            self.save_map_to_memory(self.selected_map_file)  # Save current map state
                            old_map = self.selected_map_file
                            self.selected_map_file = map_file
                            self.spawns = copy.deepcopy(self.map_spawns[map_file])
                            self.save_changes()
                            
                            # Switch back to original map
                            self.selected_map_file = old_map
                            self.spawns = copy.deepcopy(self.map_spawns[old_map])
        
        # Close the application
        self.root.destroy()

def main():
    # If running from src directory, move up one level
    if os.path.basename(os.getcwd()) == 'src':
        os.chdir('..')
        print(f"Changed working directory to: {os.getcwd()}")
        
    root = tk.Tk()
    app = MonsterSpawnEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
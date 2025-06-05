import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import binascii
import traceback
try:
    from PIL import Image, ImageTk
except ImportError:
    print("Pillow library not installed. Image handling will be disabled.")
    Image = None
    ImageTk = None

class YGOISOPatcher:
    def __init__(self, root):
        self.root = root
        self.root.title("YGO ISO Patcher")
        self.iso_path = None
        self.wamrg_path = None
        self.slus_path = None
        self.applied_patches = []
        self.selected_opponent = tk.StringVar()
        self.opponent_data = {}
        self.card_names = {}
        self.card_descriptions = {}
        self.card_stats = {}  # Placeholder for ATK/DEF
        self.card_droppers = {}  # Maps card_id to list of opponents who drop it
        self.last_search_text = ""  # To persist search across views
        self.char_map = {
            0x18: "A", 0x2D: "B", 0x2B: "C", 0x20: "D", 0x25: "E", 0x31: "F", 0x29: "G",
            0x23: "H", 0x1A: "I", 0x3B: "J", 0x33: "K", 0x2A: "L", 0x1E: "M", 0x2C: "N",
            0x21: "O", 0x2F: "P", 0x3E: "Q", 0x26: "R", 0x1D: "S", 0x1C: "T", 0x35: "U",
            0x39: "V", 0x22: "W", 0x46: "X", 0x24: "Y", 0x3F: "Z",
            0x03: "a", 0x15: "b", 0x0F: "c", 0x0C: "d", 0x01: "e", 0x13: "f", 0x10: "g",
            0x09: "h", 0x05: "i", 0x34: "j", 0x16: "k", 0x0A: "l", 0x0E: "m", 0x06: "n",
            0x04: "o", 0x14: "p", 0x37: "q", 0x08: "r", 0x07: "s", 0x02: "t", 0x0D: "u",
            0x19: "v", 0x12: "w", 0x36: "x", 0x11: "y", 0x32: "z",
            0x38: "0", 0x3D: "1", 0x3A: "2", 0x41: "3", 0x4A: "4", 0x42: "5", 0x4E: "6",
            0x45: "7", 0x57: "8", 0x59: "9",
            0x00: " ", 0x30: "-", 0x3C: "#", 0x43: "&", 0x0B: ".", 0x1F: ",", 0x55: "a",
            0x17: "!", 0x1B: "'", 0x27: "<", 0x28: ">", 0x2E: "?", 0x44: "/", 0x48: ":",
            0x4B: ")", 0x4C: "(", 0x4F: "$", 0x50: "*", 0x51: ">", 0x54: "<", 0x40: "\"",
            0x56: "+", 0x5B: "%",
            0xFF: "",  # Terminator
            0x5C: "@", 0x5D: "^", 0x5E: "~", 0x5F: "_", 0x60: "`", 0x61: "{", 0x62: "}",
            0x63: "[", 0x64: "]", 0x65: "=", 0x66: ";", 0x67: "\\",
            0x47: " ", 0x6F: "?", 0x77: "?", 0x7F: "?", 0x8F: "?", 0x97: "?", 0x9F: "?",
            0xAF: "?", 0xB7: "?", 0xC7: "?", 0xE7: "?", 0xEF: "?", 0xF7: "?",
        }
        self.opponents = []
        self.card_types = {}
        self.card_images = {}
        self.photo_references = []
        self.total_cards = 722
        self.drop_chances = {
            1: 0, 2: 100, 3: 0, 4: 100, 5: 48
        }

        # Offsets for deck and drop data in WA_MRG.MRG
        self.wamrg_offsets = {
            "deck": 0x0000,
            "sa_pow_drops": 0x05B4,
            "bcd_drops": 0x0B68,
            "sa_tec_drops": 0x111C,
        }
        self.data_size = 1460
        self.opponent_block_size = 0x1800

        # Known game info offsets
        self.game_info_offsets = {
            "types_start": 0x1C92CE,
            "guardian_stars_start": 0x1C9380,
            "opponents_start": 0x1C93D0,
            "locations_start": 0x1C959A,
            "scrambled_data_start": 0x1C9804,
            "scrambled_data_end": 0x1C98CB,
            "card_desc_pointers_start": 0x1B0A02,
            "card_desc_text_base": 0x1B0800,
        }

        # Card image mappings
        self.card_image_map = {
            "magic": "Image_Card_Magic_Small",
            "normal": "Image_Card_Normal_Small",
            "ritual": "Image_Card_Ritual_Small",
            "trap": "Image_Card_Trap_Small",
            "base": "Image_Base_Card_Small"
        }
        self.image_base_path = "./card_images/"
        if not os.path.exists(self.image_base_path):
            os.makedirs(self.image_base_path)

        # Initial GUI Setup
        self.setup_initial_gui()

    def setup_initial_gui(self):
        """Set up the initial interface with file selection and two buttons, greyed out initially with readable text."""
        self.iso_label = tk.Label(self.root, text="Select ISO/BIN File:")
        self.iso_label.pack()
        self.iso_display = tk.Label(self.root, text="No ISO file selected")
        self.iso_display.pack()
        self.select_iso_button = tk.Button(self.root, text="Select ISO File", command=self.select_iso)
        self.select_iso_button.pack()

        self.slus_label = tk.Label(self.root, text="Select SLUS File (SLUS_014.11):")
        self.slus_label.pack()
        self.slus_display = tk.Label(self.root, text="No SLUS file selected")
        self.slus_display.pack()
        self.select_slus_button = tk.Button(self.root, text="Select SLUS File", command=self.select_slus)
        self.select_slus_button.pack()

        self.wamrg_label = tk.Label(self.root, text="Select WAMRG File (optional):")
        self.wamrg_label.pack()
        self.wamrg_display = tk.Label(self.root, text="No WAMRG file selected")
        self.wamrg_display.pack()
        self.select_wamrg_button = tk.Button(self.root, text="Select WAMRG File", command=self.select_wamrg)
        self.select_wamrg_button.pack()

        self.patch_button = tk.Button(self.root, text="Patch ISO", command=self.show_patch_interface, bg="#C0C0C0", fg="#000000")
        self.patch_button.pack(pady=10)

        self.view_button = tk.Button(self.root, text="View Data", command=self.show_view_data_interface, bg="#C0C0C0", fg="#000000")
        self.view_button.pack(pady=10)

    def select_iso(self):
        self.iso_path = filedialog.askopenfilename(filetypes=[("ISO/BIN files", "*.iso *.bin")])
        self.iso_display.config(text=self.iso_path or "No ISO file selected")
        if self.iso_path:
            try:
                self.extract_files()
                self.patch_button.config(bg="#008000", fg="white")
                self.view_button.config(bg="#C0C0C0", fg="#000000") if not (self.slus_path and self.wamrg_path) else None
            except Exception as e:
                messagebox.showerror("Error", f"Failed to process ISO: {e}")
                traceback.print_exc()
        else:
            self.patch_button.config(bg="#C0C0C0", fg="#000000")

    def select_slus(self):
        self.slus_path = filedialog.askopenfilename(filetypes=[("SLUS files", "SLUS_014.11")])
        self.slus_display.config(text=self.slus_path or "No SLUS file selected")
        if self.slus_path:
            try:
                with open(self.slus_path, "rb") as f:
                    slus_data = f.read()
                self.load_opponent_names(slus_data)
                self.load_card_names(slus_data)
                self.load_card_descriptions(slus_data)
                self.load_card_stats(slus_data)  # Placeholder for ATK/DEF
                self.view_button.config(bg="#0000FF", fg="white" if self.wamrg_path else "#000000")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load SLUS file: {e}")
                traceback.print_exc()
        else:
            self.view_button.config(bg="#C0C0C0", fg="#000000")

    def select_wamrg(self):
        self.wamrg_path = filedialog.askopenfilename(filetypes=[("WAMRG files", "*.dat *.mrg")])
        self.wamrg_display.config(text=self.wamrg_path or "No WAMRG file selected")
        if self.wamrg_path:
            try:
                self.precompute_card_droppers()
                self.view_button.config(bg="#0000FF", fg="white" if self.slus_path else "#000000")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load WAMRG data: {e}")
                traceback.print_exc()
        else:
            self.view_button.config(bg="#C0C0C0", fg="#000000")

    def extract_files(self):
        pass

    def load_opponent_names(self, slus_data):
        self.opponents.clear()
        offset = self.game_info_offsets["opponents_start"]
        max_length = 50
        expected_opponents = 40

        print(f"Loading opponent names starting at offset {hex(offset)}")
        opponent_id = 0

        while opponent_id < expected_opponents:
            name = ""
            i = 0
            try:
                if slus_data[offset:offset + 3] == bytes([0xF8, slus_data[offset + 1], slus_data[offset + 2]]):
                    i = 3
                    offset += 3
                while i < max_length:
                    byte = slus_data[offset + i]
                    if byte == 0xFF:
                        print(f"Found FF terminator at {hex(offset + i)} for opponent {opponent_id}")
                        break
                    char = self.char_map.get(byte, f"?[{hex(byte)}]")
                    name += char
                    i += 1
                offset += i + 1
            except IndexError:
                print(f"Invalid offset {hex(offset)} for opponent {opponent_id}, reached end of SLUS data")
                name = f"Unknown_{opponent_id}"
                break

            name = name.strip().title() if name else f"Unknown_{opponent_id}"
            self.opponents.append(name)
            print(f"Opponent {opponent_id}: {name} at offset {hex(offset - i - 1)}, bytes: {binascii.hexlify(slus_data[offset - i - 1:offset - 1])}")
            opponent_id += 1

        print(f"Loaded {len(self.opponents)} opponent names from SLUS file")

    def load_card_names(self, slus_data):
        self.card_names.clear()
        pointer_base = 0x1C6000
        max_length = 100

        print(f"Using pointer base: {hex(pointer_base)}")
        card_id = 1
        pointer_offset = 2  # Skip the first pointer as a placeholder

        while card_id <= self.total_cards:
            idx = pointer_base + pointer_offset
            if idx + 1 >= len(slus_data):
                print(f"Pointer offset {hex(idx)} exceeds SLUS data length {hex(len(slus_data))}")
                break
            pointer_bytes = slus_data[idx:idx + 2]
            pointer_little = int.from_bytes(pointer_bytes, 'little')
            pointer_big = int.from_bytes(pointer_bytes, 'big')
            #print(f"Card {card_id} raw pointer bytes at {hex(idx)}: {binascii.hexlify(pointer_bytes)} (little-endian: {hex(pointer_little)}, big-endian: {hex(pointer_big)})")
            
            pointer = pointer_little
            text_offset = 0x1C0800 + pointer
            #print(f"Card {card_id} pointer: {hex(pointer)} (raw offset {hex(idx)}, calculated text offset {hex(text_offset)})")
            
            name = ""
            i = 0
            try:
                if slus_data[text_offset:text_offset + 3] == bytes([0xF8, slus_data[text_offset + 1], slus_data[text_offset + 2]]):
                    i = 3
                while i < max_length:
                    byte = slus_data[text_offset + i]
                    if byte == 0xFF:
                        #print(f"Found FF terminator at {hex(text_offset + i)} for card {card_id}")
                        break
                    char = self.char_map.get(byte, f"?[{hex(byte)}]")
                    name += char
                    i += 1
            except IndexError:
                print(f"Invalid text offset {hex(text_offset)} for card {card_id}, name data may be outside SLUS or offset needs adjustment")
                name = f"Unknown_{card_id}"
                card_id += 1
                pointer_offset += 2
                continue
            
            name = name.strip().title() if name else f"Unknown_{card_id}"
            self.card_names[card_id] = name
            #if card_id in [1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 35, 167, 216, 237, 311, 323, 335, 336, 340, 349, 363, 433, 551, 558, 591, 665, 666, 677, 681, 682, 688, 674, 722]:
            #    print(f"Card {card_id}: {name} at text offset {hex(text_offset)}, bytes: {binascii.hexlify(slus_data[text_offset:text_offset + i] if text_offset + i <= len(slus_data) else b'offset exceeds SLUS')}")
            card_id += 1
            pointer_offset += 2

        print(f"Loaded {len(self.card_names)} card names from SLUS file")

    def load_card_descriptions(self, slus_data):
        self.card_descriptions.clear()
        pointer_base = self.game_info_offsets["card_desc_pointers_start"]
        text_base = self.game_info_offsets["card_desc_text_base"]
        max_length = 200

        print(f"Using pointer base: {hex(pointer_base)}, text base: {hex(text_base)}")
        card_id = 1
        pointer_offset = 0  # Start at 0x1B0A00

        while card_id <= self.total_cards:
            idx = pointer_base + pointer_offset
            if idx + 1 >= len(slus_data):
                print(f"Pointer offset {hex(idx)} exceeds SLUS data length {hex(len(slus_data))}")
                break
            pointer_bytes = slus_data[idx:idx + 2]
            pointer_little = int.from_bytes(pointer_bytes, 'little')
            pointer_big = int.from_bytes(pointer_bytes, 'big')
            #print(f"Card {card_id} description pointer bytes at {hex(idx)}: {binascii.hexlify(pointer_bytes)} (little-endian: {hex(pointer_little)}, big-endian: {hex(pointer_big)})")
            
            if card_id == 1:
                # Skip the placeholder pointer at 0x1B0A00 (0xF409), move to 0x1B0A02 for Card 1
                pointer_offset = 0
                idx = pointer_base + pointer_offset
                pointer_bytes = slus_data[idx:idx + 2]
                pointer_little = int.from_bytes(pointer_bytes, 'little')
                pointer_big = int.from_bytes(pointer_bytes, 'big')
                print(f"Adjusted Card 1 description pointer bytes at {hex(idx)}: {binascii.hexlify(pointer_bytes)} (little-endian: {hex(pointer_little)}, big-endian: {hex(pointer_big)})")
            
            pointer = pointer_little
            text_offset = text_base + pointer
            #print(f"Card {card_id} description pointer: {hex(pointer)}, calculated text offset: {hex(text_offset)}")
            
            desc = ""
            i = 0
            try:
                if slus_data[text_offset:text_offset + 3] == bytes([0xF8, slus_data[text_offset + 1], slus_data[text_offset + 2]]):
                    i = 3
                while i < max_length:
                    byte = slus_data[text_offset + i]
                    if byte == 0xFF:
                     #   print(f"Found FF terminator at {hex(text_offset + i)} for card {card_id} description")
                       break
                    char = self.char_map.get(byte, f"?[{hex(byte)}]")
                    desc += char
                    i += 1
            except IndexError:
                print(f"Invalid text offset {hex(text_offset)} for card {card_id} description, data may be outside SLUS")
                desc = f"Unknown_{card_id}"
                card_id += 1
                pointer_offset += 2
                continue
            
            desc = desc.strip() if desc else f"Unknown_{card_id}"
            self.card_descriptions[card_id] = desc
            # Commented out debug lines as requested
            # print(f"Card 722 description pointer bytes at 0x1b0fa2: b'f6cd' (little-endian: 0xcdf6, big-endian: 0xf6cd)")
            # print(f"Card 722 description pointer: 0xcdf6, calculated text offset: 0x1bd5f6")
            # print(f"Found FF terminator at 0x1bd640 for card 722 description")
            # print(f"Card 722 description: Ceremony conducted?[0xfe]to summon the God?[0xfe]Creator of Light.?[0xfe]Sacrifice required. at text offset 0x1bd5f6, bytes: b'2b0108010e040611000f04060c0d0f02010cfe020400070d0e0e0406000209010029040cfe2b080103020408000413002a051009020bfe1d030f080513050f01000801370d0508010c0b'")
            #if card_id in [1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 35, 167, 216, 237, 311, 323, 335, 336, 340, 349, 363, 433, 551, 558, 591, 665, 666, 677, 681, 682, 688, 674, 721]:
                #print(f"Card {card_id} description: {desc} at text offset {hex(text_offset)}, bytes: {binascii.hexlify(slus_data[text_offset:text_offset + i] if text_offset + i <= len(slus_data) else b'offset exceeds SLUS')}")
            card_id += 1
            pointer_offset += 2

        print(f"Loaded {len(self.card_descriptions)} card descriptions from SLUS file")

    def load_card_stats(self, slus_data):
        """Placeholder for loading card ATK/DEF stats."""
        for card_id in range(1, self.total_cards + 1):
            self.card_stats[card_id] = {"atk": "N/A", "def": "N/A"}

    def precompute_card_droppers(self):
        """Precompute which opponents drop each card for reverse lookup."""
        self.card_droppers.clear()
        for card_id in range(1, self.total_cards + 1):
            self.card_droppers[card_id] = {"sa_pow": [], "bcd": [], "sa_tec": []}

        try:
            with open(self.wamrg_path, 'rb') as f:
                for opponent_id in range(1, len(self.opponents)):
                    opponent_name = self.opponents[opponent_id]
                    base_offset = 0xE99800 + (opponent_id * self.opponent_block_size)

                    # S/A POW Drops
                    f.seek(base_offset + self.wamrg_offsets["sa_pow_drops"])
                    sa_pow_data = f.read(self.data_size)
                    sa_pow_chances = self.parse_drop_chances(sa_pow_data, "sa_pow")
                    for card_id, chance in sa_pow_chances.items():
                        self.card_droppers[card_id]["sa_pow"].append((opponent_name, chance))

                    # B/C/D Drops
                    f.seek(base_offset + self.wamrg_offsets["bcd_drops"])
                    bcd_data = f.read(self.data_size)
                    bcd_chances = self.parse_drop_chances(bcd_data, "bcd")
                    for card_id, chance in bcd_chances.items():
                        self.card_droppers[card_id]["bcd"].append((opponent_name, chance))

                    # S/A TEC Drops
                    f.seek(base_offset + self.wamrg_offsets["sa_tec_drops"])
                    sa_tec_data = f.read(self.data_size)
                    sa_tec_chances = self.parse_drop_chances(sa_tec_data, "sa_tec")
                    for card_id, chance in sa_tec_chances.items():
                        self.card_droppers[card_id]["sa_tec"].append((opponent_name, chance))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to precompute card droppers: {e}")
            traceback.print_exc()

    def show_patch_interface(self):
        """Display the patching interface in a new window."""
        if not self.iso_path:
            messagebox.showerror("Error", "Please select an ISO file first.")
            return

        patch_window = tk.Toplevel(self.root)
        patch_window.title("Patch ISO")
        patch_window.geometry("400x400")

        tk.Label(patch_window, text="Select Patches to Apply:", font=("Arial", 12, "bold")).pack(pady=10)

        self.patch_vars = {}
        patches = [
            ("Drop Data Modifier", "drop_modifier"),
            ("Exodia S-TEC Win", "exodia_stec"),
            ("No Password Limit", "password"),
            ("Convert Repeatable Cards to Starchips", "convert_cards"),
            ("Remove Win Limiter", "win_limiter"),
        ]

        for patch_name, patch_key in patches:
            self.patch_vars[patch_key] = tk.BooleanVar()
            frame = tk.Frame(patch_window)
            frame.pack(fill=tk.X, padx=10)
            tk.Checkbutton(frame, text=f"Enable {patch_name}", variable=self.patch_vars[patch_key]).pack(side=tk.LEFT)
            tk.Checkbutton(frame, text=f"Disable {patch_name}", variable=self.patch_vars[patch_key], onvalue=False, offvalue=True).pack(side=tk.LEFT)

        apply_button = tk.Button(patch_window, text="Apply Patches", command=self.apply_patches, bg="green", fg="white")
        apply_button.pack(pady=20)

    def apply_patches(self):
        """Apply the selected patches to the ISO."""
        self.applied_patches.clear()
        try:
            if self.patch_vars['drop_modifier'].get():
                self.apply_drop_modifier_patch()
            if self.patch_vars['exodia_stec'].get():
                self.apply_exodia_stec_patch()
            if self.patch_vars['password'].get():
                self.apply_password_patch()
            if self.patch_vars['convert_cards'].get():
                self.apply_convert_cards_patch()
            if self.patch_vars['win_limiter'].get():
                self.apply_win_limiter_patch()

            if self.applied_patches:
                messagebox.showinfo("Success", f"Applied patches: {', '.join(self.applied_patches)}")
            else:
                messagebox.showinfo("Info", "No patches applied.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to patch ISO: {e}")
            traceback.print_exc()

    def apply_drop_modifier_patch(self):
        self.applied_patches.append("Drop Data Modifier")

    def apply_exodia_stec_patch(self):
        self.applied_patches.append("Exodia S-TEC Win")

    def apply_password_patch(self):
        self.applied_patches.append("No Password Limit")

    def apply_convert_cards_patch(self):
        self.applied_patches.append("Convert Repeatable Cards to Starchips")

    def apply_win_limiter_patch(self):
        self.applied_patches.append("Remove Win Limiter")

    def show_view_data_interface(self):
        """Display the data viewing interface in a new window."""
        if not self.wamrg_path or not self.slus_path:
            messagebox.showerror("Error", "Please select both SLUS and WAMRG files first.")
            return

        view_window = tk.Toplevel(self.root)
        view_window.title("View Data")
        view_window.geometry("800x600")

        # Opponent Selection
        tk.Label(view_window, text="Select Opponent:", font=("Arial", 12, "bold")).pack(pady=5)
        self.selected_opponent.set("")
        opponent_menu = ttk.OptionMenu(view_window, self.selected_opponent, "", *self.opponents, command=self.load_opponent_data_view)
        opponent_menu.pack()

        # Notebook for Views
        self.notebook = ttk.Notebook(view_window)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # Setup Tabs with Treeview and Search
        self.deck_frame = tk.Frame(self.notebook)
        self.setup_treeview(self.deck_frame, "Deck")
        self.add_search_bar(self.deck_frame, self.deck_tree, "deck")
        self.notebook.add(self.deck_frame, text="Deck")

        self.sa_pow_frame = tk.Frame(self.notebook)
        self.setup_treeview(self.sa_pow_frame, "S/A POW Drops")
        self.add_search_bar(self.sa_pow_frame, self.sa_pow_tree, "sa_pow")
        self.notebook.add(self.sa_pow_frame, text="S/A POW Drops")

        self.bcd_frame = tk.Frame(self.notebook)
        self.setup_treeview(self.bcd_frame, "B/C/D Drops")
        self.add_search_bar(self.bcd_frame, self.bcd_tree, "bcd")
        self.notebook.add(self.bcd_frame, text="B/C/D Drops")

        self.sa_tec_frame = tk.Frame(self.notebook)
        self.setup_treeview(self.sa_tec_frame, "S/A TEC Drops")
        self.add_search_bar(self.sa_tec_frame, self.sa_tec_tree, "sa_tec")
        self.notebook.add(self.sa_tec_frame, text="S/A TEC Drops")

        self.all_cards_frame = tk.Frame(self.notebook)
        self.setup_treeview_with_scrollbar(self.all_cards_frame, "All Cards")
        self.add_search_bar(self.all_cards_frame, self.all_cards_tree, "all_cards")
        self.notebook.add(self.all_cards_frame, text="All Cards")

        # Card Info Panel
        self.card_info_frame = tk.Frame(view_window)
        self.card_info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.card_info_text = tk.Text(self.card_info_frame, height=10, width=80)
        self.card_info_text.pack(fill=tk.BOTH, expand=True)

        # Load initial data with last search
        self.load_opponent_data_view()
        self.load_all_cards_view()

    def setup_treeview(self, frame, view_name):
        """Set up a Treeview table for a given view (without scrollbar)."""
        if view_name == "All Cards":
            columns = ("Card ID", "Card Name", "ATK/DEF", "Description")
            tree = ttk.Treeview(frame, columns=columns, show="headings")
            tree.heading("Card ID", text="Card ID")
            tree.heading("Card Name", text="Card Name")
            tree.heading("ATK/DEF", text="ATK/DEF")
            tree.heading("Description", text="Description")
            tree.column("Card ID", width=60)
            tree.column("Card Name", width=200)
            tree.column("ATK/DEF", width=100)
            tree.column("Description", width=300)
        else:
            columns = ("Card ID", "Card Name", "ATK/DEF", "Chance")
            tree = ttk.Treeview(frame, columns=columns, show="headings")
            tree.heading("Card ID", text="Card ID")
            tree.heading("Card Name", text="Card Name")
            tree.heading("ATK/DEF", text="ATK/DEF")
            tree.heading("Chance", text="Chance (%)")
            tree.column("Card ID", width=60)
            tree.column("Card Name", width=200)
            tree.column("ATK/DEF", width=100)
            tree.column("Chance", width=100)

        tree.pack(fill=tk.BOTH, expand=True)

        # Bind click event to show card info
        tree.bind("<<TreeviewSelect>>", lambda event, t=tree: self.show_card_info(t, view_name.lower().replace(" ", "_").replace("/", "_")))

        # Store the treeview for later updates
        if view_name == "Deck":
            self.deck_tree = tree
        elif view_name == "S/A POW Drops":
            self.sa_pow_tree = tree
        elif view_name == "B/C/D Drops":
            self.bcd_tree = tree
        elif view_name == "S/A TEC Drops":
            self.sa_tec_tree = tree
        elif view_name == "All Cards":
            self.all_cards_tree = tree

    def setup_treeview_with_scrollbar(self, frame, view_name):
        """Set up a Treeview table with a scrollbar for the 'All Cards' view."""
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        columns = ("Card ID", "Card Name", "ATK/DEF", "Description")
        tree = ttk.Treeview(scrollable_frame, columns=columns, show="headings")
        tree.heading("Card ID", text="Card ID")
        tree.heading("Card Name", text="Card Name")
        tree.heading("ATK/DEF", text="ATK/DEF")
        tree.heading("Description", text="Description")
        tree.column("Card ID", width=60)
        tree.column("Card Name", width=200)
        tree.column("ATK/DEF", width=100)
        tree.column("Description", width=300)

        tree.bind("<<TreeviewSelect>>", lambda event: self.show_card_info(tree, view_name.lower().replace(" ", "_").replace("/", "_")))

        tree.pack(fill=tk.BOTH, expand=True)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.all_cards_tree = tree

    def add_search_bar(self, frame, tree, data_type):
        """Add a search bar below the Treeview with auto-search."""
        tree.pack(fill=tk.BOTH, expand=True)  # Ensure Treeview is packed first
        search_frame = tk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = tk.Entry(search_frame)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda event: self.update_search(tree, search_entry, data_type))

    def update_search(self, tree, search_entry, data_type):
        """Update the search text and filter the Treeview."""
        self.last_search_text = search_entry.get()
        self.filter_treeview(tree, self.last_search_text, data_type)

    def filter_treeview(self, tree, search_text, data_type):
        """Filter the Treeview based on search text."""
        search_text = search_text.lower()
        for item in tree.get_children():
            tree.delete(item)

        if data_type == "all_cards":
            for card_id in range(1, self.total_cards + 1):
                card_name = self.card_names.get(card_id, f"Unknown_{card_id}").lower()
                stats = self.card_stats.get(card_id, {"atk": "N/A", "def": "N/A"})
                atk_def = f"{stats['atk']}/{stats['def']}".lower()
                card_desc = self.card_descriptions.get(card_id, "").lower()
                if search_text in str(card_id) or search_text in card_name or search_text in atk_def or search_text in card_desc:
                    tree.insert("", tk.END, values=(card_id, card_name.title(), atk_def, card_desc), tags=(card_id, "all_cards"))
        else:
            chances = self.opponent_data.get(data_type, {})
            for card_id, chance in chances.items():
                card_name = self.card_names.get(card_id, f"Unknown_{card_id}").lower()
                stats = self.card_stats.get(card_id, {"atk": "N/A", "def": "N/A"})
                atk_def = f"{stats['atk']}/{stats['def']}".lower()
                percentage = chance / 2048 * 100
                if search_text in str(card_id) or search_text in card_name or search_text in atk_def:
                    tree.insert("", tk.END, values=(card_id, card_name.title(), atk_def, f"{percentage:.2f}%"), tags=(card_id, data_type))

    def load_opponent_data_view(self, event=None):
        """Load opponent data and update the Treeview tables with last search."""
        if not self.wamrg_path or not self.selected_opponent.get():
            return
        opponent_name = self.selected_opponent.get()
        if not opponent_name or opponent_name == self.opponents[0]:
            return
        opponent_id = self.opponents.index(opponent_name)
        if opponent_id == 0:
            return

        try:
            with open(self.wamrg_path, 'rb') as f:
                print(f"Loading from: {self.wamrg_path}, Size: {os.path.getsize(self.wamrg_path)} bytes")
                base_offset = 0xE99800 + (opponent_id * self.opponent_block_size)
                print(f"Base offset for {opponent_name} (ID {opponent_id}): {hex(base_offset)}")

                # Deck
                f.seek(base_offset + self.wamrg_offsets["deck"])
                deck_data = f.read(self.data_size)
                deck_chances = self.parse_deck(deck_data)
                self.opponent_data["deck"] = deck_chances
                self.update_treeview(self.deck_tree, deck_chances, "deck")

                # S/A POW Drops
                f.seek(base_offset + self.wamrg_offsets["sa_pow_drops"])
                sa_pow_data = f.read(self.data_size)
                sa_pow_chances = self.parse_drop_chances(sa_pow_data, "sa_pow")
                self.opponent_data["sa_pow"] = sa_pow_chances
                self.update_treeview(self.sa_pow_tree, sa_pow_chances, "sa_pow")

                # B/C/D Drops
                f.seek(base_offset + self.wamrg_offsets["bcd_drops"])
                bcd_data = f.read(self.data_size)
                bcd_chances = self.parse_drop_chances(bcd_data, "bcd")
                self.opponent_data["bcd"] = bcd_chances
                self.update_treeview(self.bcd_tree, bcd_chances, "bcd")

                # S/A TEC Drops
                f.seek(base_offset + self.wamrg_offsets["sa_tec_drops"])
                sa_tec_data = f.read(self.data_size)
                sa_tec_chances = self.parse_drop_chances(sa_tec_data, "sa_tec")
                self.opponent_data["sa_tec"] = sa_tec_chances
                self.update_treeview(self.sa_tec_tree, sa_tec_chances, "sa_tec")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load opponent data: {e}")
            traceback.print_exc()

    def load_all_cards_view(self):
        """Load and display all cards in the Treeview table with last search."""
        if not self.all_cards_tree:
            return

        # Clear existing entries
        for item in self.all_cards_tree.get_children():
            self.all_cards_tree.delete(item)

        # Insert all cards based on last search
        self.filter_treeview(self.all_cards_tree, self.last_search_text, "all_cards")

    def update_treeview(self, tree, chances, data_type):
        """Update the Treeview with the given data and last search."""
        # Clear existing entries
        for item in tree.get_children():
            tree.delete(item)

        # Insert new data based on last search
        self.filter_treeview(tree, self.last_search_text, data_type)

    def show_card_info(self, tree, data_type):
        """Display card info and droppers when a card is clicked."""
        selected_item = tree.selection()
        if not selected_item:
            return
        card_id = int(tree.item(selected_item)["values"][0])
        
        card_name = self.card_names.get(card_id, f"Unknown_{card_id}")
        card_desc = self.card_descriptions.get(card_id, "No description available")
        stats = self.card_stats.get(card_id, {"atk": "N/A", "def": "N/A"})
        atk_def = f"{stats['atk']}/{stats['def']}"

        droppers = self.card_droppers.get(card_id, {"sa_pow": [], "bcd": [], "sa_tec": []})
        sa_pow_droppers = "\n".join([f"{opp}: {chance/2048*100:.2f}%" for opp, chance in droppers["sa_pow"]]) or "None"
        bcd_droppers = "\n".join([f"{opp}: {chance/2048*100:.2f}%" for opp, chance in droppers["bcd"]]) or "None"
        sa_tec_droppers = "\n".join([f"{opp}: {chance/2048*100:.2f}%" for opp, chance in droppers["sa_tec"]]) or "None"

        info_text = (
            f"Card ID: {card_id}\n"
            f"Name: {card_name}\n"
            f"ATK/DEF: {atk_def}\n"
            f"Description: {card_desc}\n\n"
            f"Dropped by (S/A POW):\n{sa_pow_droppers}\n\n"
            f"Dropped by (B/C/D):\n{bcd_droppers}\n\n"
            f"Dropped by (S/A TEC):\n{sa_tec_droppers}\n"
        )

        self.card_info_text.delete(1.0, tk.END)
        self.card_info_text.insert(tk.END, info_text)

    def parse_deck(self, data):
        chances = {}
        for card_id in range(1, self.total_cards + 1):
            idx = (card_id - 1) * 2
            if idx + 2 > len(data):
                break
            chance = int.from_bytes(data[idx:idx + 2], 'little')
            if chance > 0:
                chances[card_id] = chance
        return chances

    def parse_drop_chances(self, data, drop_type):
        chances = {}
        for card_id in range(1, self.total_cards + 1):
            idx = (card_id - 1) * 2
            if idx + 2 > len(data):
                break
            chance = int.from_bytes(data[idx:idx + 2], 'little')
            if chance > 0:
                chances[card_id] = chance
        return chances

    def get_card_image_path(self, card_id):
        card_type = self.card_types.get(card_id, "normal")
        image_name = self.card_image_map.get(card_type, self.card_image_map["base"])
        return os.path.join(self.image_base_path, f"{image_name}.png")

if __name__ == "__main__":
    root = tk.Tk()
    app = YGOISOPatcher(root)
    root.mainloop()
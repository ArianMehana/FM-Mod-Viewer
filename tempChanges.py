import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import binascii
import traceback
import re
from PIL import Image, ImageTk


class YGOISOPatcher:
    def __init__(self, root):
        self.root = root
        self.root.title("YGO ISO Patcher")
        self.iso_path = None # Path to the selected ISO/BIN file
        self.wamrg_path = None # Path to WAMRG.MRG or WAMRG.DAT
        self.slus_path = None # Path to SLUS_014.11
        self.applied_patches = [] # List to track applied patches
        self.selected_opponent = tk.StringVar()
        self.opponent_data = {} # Maps opponent_id to (name, sa_pow_drops, bcd_drops, sa_tec_drops)
        self.card_names = {} # Maps card_id to name
        self.card_descriptions = {} # Maps card_id to description
        self.card_stats = {}  # Placeholder for ATK/DEF
        self.card_droppers = {}  # Maps card_id to list of opponents who drop it
        self.card_passwords_and_costs = {}  # Maps card_id to (password, cost)
        self.card_to_equips = {} # Maps card_id to list of equip cards
        self.force_apply = tk.BooleanVar(value=False)
        self.search_terms = {
            "deck": "",
            "sa_pow": "",
            "bcd": "",
            "sa_tec": "",
            "all_cards": ""
        }  # Separate search term for each view
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
        self.drop_rate_addresses = {
            '1D00D7': '6500',  # Default: 100 cards
            '0C00D7': '6500',  # Default: 100 cards
            '0200D7': '6400'   # Default: 100 cards
        }
        self.drop_chances = {
            1: 0, 2: 100, 3: 0, 4: 100, 5: 48
        }

        self.card_attributes_map = {
            0x00: "Light",
            0x01: "Dark",
            0x02: "Earth",
            0x03: "Water",
            0x04: "Fire",
            0x05: "Wind",
            0x06: "Spell",
            0x07: "Trap",
            0x08: "Divine",
        }
        # Offsets for deck and drop data in WA_MRG.MRG
        self.wamrg_offsets = {
            "deck": 0x0000,
            "sa_pow_drops": 0x05B4,
            "bcd_drops": 0x0B68,
            "sa_tec_drops": 0x111C,
        }
        self.card_types_map = {}
        self.guardian_stars_map = {}
        self.data_size = 1460
        self.opponent_block_size = 0x1800

        # Known game info offsets
        self.game_info_offsets = {
            "types_start": 0x1C93D0,
            "guardian_stars_start": 0x1C9380,
            "opponents_start": 0x1C92CE, 
            "locations_start": 0x1C959A,
            "scrambled_data_start": 0x1C9804,
            "scrambled_data_end": 0x1C98CB,
            "card_desc_pointers_start": 0x1B0A00,
            "card_desc_text_base": 0x1B0800,
        }

        #Drop rate changer
        self.drop_rate_patches = [
            {'original': bytes.fromhex("1B001D3C00AC"), 'modified': bytes.fromhex("1E801D3C00C0"), 'patch_name': 'Drop Rate (1B001D3C00AC)'},
            {'original': bytes.fromhex("A32000B693"), 'modified': bytes.fromhex("A72000B697"), 'patch_name': 'Drop Rate (A32000B693)'},
            {'original': bytes.fromhex("A32000B6A3"), 'modified': bytes.fromhex("A72000B6A7"), 'patch_name': 'Drop Rate (A32000B6A3)'},
            {'original': bytes.fromhex("1B80043C00AC"), 'modified': bytes.fromhex("1E80043C00C0"), 'patch_name': 'Drop Rate (1B80043C00AC)'},
            {'original': bytes.fromhex("A220005692"), 'modified': bytes.fromhex("A620005696"), 'patch_name': 'Drop Rate (A220005692)'},
            {'original': bytes.fromhex("A2200056A2"), 'modified': bytes.fromhex("A6200056A6"), 'patch_name': 'Drop Rate (A2200056A2)'},
            {'original': bytes.fromhex("1B80023C00AC"), 'modified': bytes.fromhex("1E80023C00C0"), 'patch_name': 'Drop Rate (1B80023C00AC)'},
            {'original': bytes.fromhex("90000000000100D626"), 'modified': bytes.fromhex("94000000000100D626"), 'patch_name': 'Drop Rate (90000000000100D626)'},
            {'original': bytes.fromhex("A0200056A0"), 'modified': bytes.fromhex("A4200056A4"), 'patch_name': 'Drop Rate (A0200056A0)'}
        ]


        #Other patches
        self.starchips_patches = [
            {'address': 0xB410, 'modified': bytes.fromhex("98FF060801004224")},
            {'address': 0x1B0660, 'modified': bytes.fromhex(
                "04004B2C1000601500000000FFFF42241D800C3CE0078C2500008D8D0000000A00AD250F000B3C3F426B3500008DAD000000002B686D010200A01100000000008BAD00000C2400000D2400000B24000062A02D860008")},
        ]
        self.password_patch = {
            'address': 0x191E7B0,  # 16504544
            'modified': bytes.fromhex("BEA90508")
        }
        self.win_patches = [
            {'original': bytes.fromhex("900106242A38C5000300E010"), 'modified': bytes.fromhex("900106242A38C50000000000")},
            {'original': bytes.fromhex("B80B06242A38C5000300E010"), 'modified': bytes.fromhex("B80B06242A38C50000000000")}
        ]
        self.exodia_patches = [
            {'original': bytes.fromhex("28000224230062"), 'modified': bytes.fromhex("81FF0224230062")},
            {'original': bytes.fromhex("28000324FF00"), 'modified': bytes.fromhex("81FF0324FF00")},
            {'original': bytes.fromhex("28000224020062"), 'modified': bytes.fromhex("81FF0224020062")}
        ]
        self.applied_patches = []
        # Card image mappings
        self.card_image_map = {
            "magic": "Image_Card_Magic_Small",
            "normal": "Image_Card_Normal_Small",
            "ritual": "Image_Card_Ritual_Small",
            "trap": "Image_Card_Trap_Small",
            "base": "Image_Base_Card_Small"
        }

        self.card_types_map = {
            0x01: "Warrior",
            0x02: "Spellcaster",
            0x03: "Fairy",
            0x04: "Fiend",
            0x05: "Dragon",
            0x06: "Zombie",
            0x07: "Machine",
            0x08: "Aqua",
            0x09: "Pyro",
            0x0A: "Spellcaster",
            0x0B: "Thunder",
            0x0C: "Dinosaur",
            0x0D: "Rock",
            0x0E: "Winged Beast",
            0x0F: "Plant",
            0x10: "Insect",
            0x11: "Beast",
            0x12: "Beast-Warrior",
            0x13: "Reptile",
            0x14: "Fish",
            0x15: "Sea Serpent",
            0x16: "Spell",
            0x17: "Trap",
            0x18: "Ritual",
            0x00: "Unknown"
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
        self.status_label = tk.Label(self.root, text="Ready", wraplength=300)
        self.status_label.pack(pady=10)

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
                self.load_type_guardian_star_names(slus_data)
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
                self.load_card_passwords_and_costs()
                self.card_to_equips = self.reverse_lookup_equips(self.wamrg_path)
                self.view_button.config(bg="#0000FF", fg="white" if self.slus_path else "#000000")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load WAMRG data: {e}")
                traceback.print_exc()
        else:
            self.view_button.config(bg="#C0C0C0", fg="#000000")

    def extract_files(self):
        pass

    
    def check_overlap(self, iso_data, change):
        original_bytes = change['original']
        modified_bytes = change['modified']
        modified_pos = iso_data.find(modified_bytes)
        original_pos = iso_data.find(original_bytes)
        is_applied = modified_pos != -1 and original_pos == -1
        return is_applied, original_bytes

    def check_overlap_address(self, iso_data, change):
        address = change['address']
        modified_bytes = change['modified']
        if address + len(modified_bytes) <= len(iso_data):
            current_bytes = iso_data[address:address + len(modified_bytes)]
            is_applied = current_bytes == modified_bytes
            return is_applied, current_bytes
        return False, None

    def parse_drop_rate_changes(self, iso_data):
        if not self.patch_vars['drop_rate'].get():
            return []
        changes = []
        # Determine which value to use for the "Drop Rate (0200D7)", "Drop Rate (1D00D7)", and "Drop Rate (0C00D7)" patches based on user selection
        # Assume self.drop_rate_var exists and is set to "100" or "1000"
        drop_rate_0200D7_value = "640017240200D712"  # default for 100
        drop_rate_1D00D7_value = "650017241D00D7"    # default for 100
        drop_rate_0C00D7_value = "650017240C00D7"    # default for 100
        if hasattr(self, "drop_rate_var") and self.drop_rate_var.get() == "1000":
            drop_rate_0200D7_value = "e80317240200d712"
            drop_rate_1D00D7_value = "e90317241D00D7"
            drop_rate_0C00D7_value = "e90317240C00D7"

        static_patches = [
            {'original': bytes.fromhex("1B001D3C00AC"), 'modified': bytes.fromhex("1E801D3C00C0"), 'patch_name': 'Drop Rate (1B001D3C00AC)'},
            {'original': bytes.fromhex("A32000B693"), 'modified': bytes.fromhex("A72000B697"), 'patch_name': 'Drop Rate (A32000B693)'},
            {'original': bytes.fromhex("100017241D00D7"), 'modified': bytes.fromhex(drop_rate_1D00D7_value), 'patch_name': 'Drop Rate (1D00D7)', 'address_key': '1D00D7'},
            {'original': bytes.fromhex("A32000B6A3"), 'modified': bytes.fromhex("A72000B6A7"), 'patch_name': 'Drop Rate (A32000B6A3)'},
            {'original': bytes.fromhex("1B80043C00AC"), 'modified': bytes.fromhex("1E80043C00C0"), 'patch_name': 'Drop Rate (1B80043C00AC)'},
            {'original': bytes.fromhex("A220005692"), 'modified': bytes.fromhex("A620005696"), 'patch_name': 'Drop Rate (A220005692)'},
            {'original': bytes.fromhex("100017240C00D7"), 'modified': bytes.fromhex(drop_rate_0C00D7_value), 'patch_name': 'Drop Rate (0C00D7)', 'address_key': '0C00D7'},
            {'original': bytes.fromhex("A2200056A2"), 'modified': bytes.fromhex("A6200056A6"), 'patch_name': 'Drop Rate (A2200056A2)'},
            {'original': bytes.fromhex("1B80023C00AC"), 'modified': bytes.fromhex("1E80023C00C0"), 'patch_name': 'Drop Rate (1B80023C00AC)'},
            {'original': bytes.fromhex("90000000000100D626"), 'modified': bytes.fromhex("94000000000100D626"), 'patch_name': 'Drop Rate (90000000000100D626)'},
            # Use the dynamic value for the "Drop Rate (0200D7)" patch
            {'original': bytes.fromhex("0F0017240200D712"), 'modified': bytes.fromhex(drop_rate_0200D7_value), 'patch_name': 'Drop Rate (0200D7)', 'address_key': '0200D7'},
            {'original': bytes.fromhex("A0200056A0"), 'modified': bytes.fromhex("A4200056A4"), 'patch_name': 'Drop Rate (A0200056A0)'}
        ]

        for patch in static_patches:
            offset = 0
            while True:
                offset = iso_data.find(patch['original'], offset)
                if offset == -1:
                    break
                change = {
                    'original': patch['original'],
                    'modified': patch['modified'],
                    'patch_name': patch['patch_name']
                }
                is_applied, _ = self.check_overlap(iso_data, change)
                if is_applied and not self.force_apply.get():
                    print(f"Patch {patch['patch_name']} already applied: {patch['modified'].hex().upper()}")
                else:
                    changes.append(change)
                offset += len(patch['original'])
        return changes

    def parse_starchips_patches(self, iso_data):
        if not self.patch_vars['starchips'].get():
            return []
        changes = []
        for patch in self.starchips_patches:
            change = {
                'address': patch['address'],
                'modified': patch['modified'],
                'patch_name': f'Starchips at {hex(patch["address"])}'
            }
            is_applied, current_bytes = self.check_overlap_address(iso_data, change)
            if is_applied and not self.force_apply.get():
                print(f"Starchips patch already applied at {hex(patch['address'])} "
                      f"(current: {current_bytes.hex().upper()})")
            else:
                if current_bytes:
                    print(f"Starchips patch at {hex(patch['address'])}: "
                          f"Current bytes {current_bytes.hex().upper()}, "
                          f"Applying {patch['modified'].hex().upper()}")
                changes.append(change)
        return changes

    def parse_password_patch(self, iso_data):
        if not self.patch_vars['password'].get():
            return []
        change = {
            'address': self.password_patch['address'],
            'modified': self.password_patch['modified'],
            'patch_name': 'No Password Limit'
        }
        is_applied, current_bytes = self.check_overlap_address(iso_data, change)
        if is_applied and not self.force_apply.get():
            print(f"No Password Limit patch already applied at {hex(change['address'])} "
                  f"(current: {current_bytes.hex().upper()})")
        else:
            if current_bytes:
                print(f"No Password Limit at {hex(change['address'])}: "
                      f"Current bytes {current_bytes.hex().upper()}, "
                      f"Applying {change['modified'].hex().upper()}")
        return [change]

    def parse_win_patches(self, iso_data):
        if not self.patch_vars['win_requirements'].get():
            return []
        changes = []
        for patch in self.win_patches:
            change = {
                'original': patch['original'],
                'modified': patch['modified'],
                'patch_name': 'Win Requirements'
            }
            is_applied, _ = self.check_overlap(iso_data, change)
            if is_applied and not self.force_apply.get():
                print(f"Win Requirements patch ({patch['modified'].hex()[:8]}) already applied")
            else:
                changes.append(change)
        return changes

    def parse_exodia_patches(self, iso_data):
        if not self.patch_vars['exodia'].get():
            return []
        changes = []
        for patch in self.exodia_patches:
            change = {
                'original': patch['original'],
                'modified': patch['modified'],
                'patch_name': 'Exodia S-Tec'
            }
            is_applied, _ = self.check_overlap(iso_data, change)
            if is_applied and not self.force_apply.get():
                print(f"Exodia S-Tec patch ({patch['modified'].hex()[:8]}) already applied")
            else:
                changes.append(change)
        return changes

    def check_and_patch_iso(self):
        if not self.iso_path or not os.path.exists(self.iso_path):
            messagebox.showerror("Error", "Please select a valid ISO/BIN file.")
            return

        if not any(self.patch_vars[key].get() for key in self.patch_vars):
            messagebox.showerror("Error", "Please select at least one patch to apply.")
            return

        with open(self.iso_path, 'rb') as f:
            iso_data = bytearray(f.read())

        self.status_label.config(text="Checking patches...")
        self.root.update()

        changes = []
        status_messages = []
        patch_key_map = {
            'Drop Rate': 'drop_rate',
            'Starchips': 'starchips',
            'No Password Limit': 'password',
            'Win Requirements': 'win_requirements',
            'Exodia S-Tec': 'exodia',
        }

        for parse_func, patch_name in [
            (self.parse_drop_rate_changes, "Drop Rate"),
            (self.parse_starchips_patches, "Starchips"),
            (self.parse_password_patch, "No Password Limit"),
            (self.parse_win_patches, "Win Requirements"),
            (self.parse_exodia_patches, "Exodia S-Tec"),
        ]:
            patch_key = patch_key_map[patch_name]
            if self.patch_vars[patch_key].get():
                patch_changes = parse_func(iso_data)
                if not patch_changes:
                    status_messages.append(f"{patch_name}: Already applied or skipped")
                else:
                    status_messages.append(f"{patch_name}: Ready to apply {len(patch_changes)} changes")
                    changes.extend(patch_changes)

        self.status_label.config(text="\n".join(status_messages))
        self.root.update()

        if not changes:
            messagebox.showinfo("Info", "No patches need to be applied.")
            return

        self.applied_patches = []
        output_file_path = os.path.splitext(self.iso_path)[0] + "_Patched" + os.path.splitext(self.iso_path)[1]

        self.status_label.config(text="Patching file...")
        self.root.update()

        for change in changes:
            if 'address' in change:
                address = change['address']
                modified_bytes = change['modified']
                if address + len(modified_bytes) <= len(iso_data):
                    original_bytes = iso_data[address:address + len(modified_bytes)]
                    iso_data[address:address + len(modified_bytes)] = modified_bytes
                    self.applied_patches.append({
                        'type': 'address',
                        'address': address,
                        'original': original_bytes,
                        'modified': modified_bytes,
                        'patch_name': change['patch_name']
                    })
                    print(f"Patched {change['patch_name']} at {hex(address)}: {modified_bytes.hex().upper()}")
                    self.status_label.config(text=f"Patched {change['patch_name']} at {hex(address)}")
                else:
                    print(f"Error: Address {hex(address)} out of range for {change['patch_name']}")
                    messagebox.showerror("Error", f"Address {hex(address)} out of range.")
            else:
                original_bytes = change['original']
                modified_bytes = change['modified']
                count = 0
                offset = 0
                while True:
                    offset = iso_data.find(original_bytes, offset)
                    if offset == -1:
                        break
                    original_region = iso_data[offset:offset + len(original_bytes)]
                    iso_data[offset:offset + len(original_bytes)] = modified_bytes[:len(original_bytes)]
                    self.applied_patches.append({
                        'type': 'search',
                        'offset': offset,
                        'original': original_region,
                        'modified': modified_bytes[:len(original_bytes)],
                        'patch_name': change['patch_name']
                    })
                    print(f"Patched {change['patch_name']} at {hex(offset)}: {modified_bytes.hex().upper()}")
                    count += 1
                    offset += len(original_bytes)
                if count == 0:
                    print(f"Warning: No matches found for {original_bytes.hex().upper()} in {change['patch_name']}")
                    self.status_label.config(text=f"No matches for {change['patch_name']}")
                else:
                    self.status_label.config(text=f"Applied {count} {change['patch_name']} patch(es)")
                self.root.update()

        with open(output_file_path, 'wb') as f:
            f.write(iso_data)

        self.status_label.config(text=f"Patched file saved to {output_file_path}")
        messagebox.showinfo("Success", f"Patched file saved to {output_file_path}")

    def reverse_patches(self):
        if not self.iso_path or not os.path.exists(self.iso_path):
            messagebox.showerror("Error", "Please select a valid ISO/BIN file.")
            return
        
        if not self.applied_patches:
            messagebox.showerror("Error", "No patches have been applied to reverse.")
            return
        
        reverse_window = tk.Toplevel(self.root)
        reverse_window.title("Reverse Patches")
        tk.Label(reverse_window, text="Select Patches to Reverse:", font=("Arial", 12)).pack(pady=10)
        
        reverse_vars = {}
        patch_names = sorted(set(patch['patch_name'] for patch in self.applied_patches))
        for name in patch_names:
            reverse_vars[name] = tk.BooleanVar(value=False)
            tk.Checkbutton(reverse_window, text=name, variable=reverse_vars[name]).pack(anchor='w', padx=10)
        
        def apply_reversal():
            with open(self.iso_path, 'rb') as f:
                iso_data = bytearray(f.read())
            
            reversed_count = 0
            for patch in self.applied_patches:
                if reverse_vars[patch['patch_name']].get():
                    if patch['type'] == 'address':
                        address = patch['address']
                        original_bytes = patch['original']
                        if address + len(original_bytes) <= len(iso_data):
                            iso_data[address:address + len(original_bytes)] = original_bytes
                            print(f"Reversed {patch['patch_name']} at {hex(address)}")
                            reversed_count += 1
                    else:
                        offset = patch['offset']
                        original_bytes = patch['original']
                        if offset + len(original_bytes) <= len(iso_data):
                            iso_data[offset:offset + len(original_bytes)] = original_bytes
                            print(f"Reversed {patch['patch_name']} at {hex(offset)}")
                            reversed_count += 1
                    self.root.update()
            
            output_file_path = os.path.splitext(self.iso_path)[0] + "_Reversed" + os.path.splitext(self.iso_path)[1]
            with open(output_file_path, 'wb') as f:
                f.write(iso_data)
            
            self.status_label.config(text=f"Reversed file saved to {output_file_path}")
            messagebox.showinfo("Success", f"Reversed {reversed_count} patch(es).")
            reverse_window.destroy()
        
        tk.Button(reverse_window, text="Apply Reversal", command=apply_reversal, bg="blue", fg="white").pack(pady=20)
    


    def load_type_guardian_star_names(self, slus_data):
        """Load Type and Guardian Star names using pointers at 0x1C6600."""
        pointer_base = 0x1C6600
        text_base = 0x1C0800
        num_type_pointers = 24  # 48 bytes = 24 pointers
        num_guardian_star_pointers = 10  # 20 bytes = 10 pointers
        max_length = 50

        # Load Types
        self.card_types_map = {}
        print(f"Loading Type names using pointers at {hex(pointer_base)}")
        for type_id in range(num_type_pointers):
            pointer_offset = pointer_base + (type_id * 2)
            if pointer_offset + 2 > len(slus_data):
                print(f"Reached end of SLUS data at type pointer {type_id}")
                break

            pointer_value = int.from_bytes(slus_data[pointer_offset:pointer_offset + 2], 'little')
            text_offset = text_base + pointer_value
            #print(f"Type {type_id}: Pointer offset = {hex(pointer_offset)}, Pointer value = {hex(pointer_value)}, Text offset = {hex(text_offset)}")

            # Read the name at the text offset, skipping multiple 0xF8 prefixes if present
            name = ""
            i = 0
            try:
                while i < max_length:
                    if text_offset + i >= len(slus_data):
                        break
                    byte = slus_data[text_offset + i]
                    if byte == 0xFF:
                        #print(f"Found FF terminator at {hex(text_offset + i)} for type {type_id}")
                        break
                    elif byte == 0xF8 and i + 2 < max_length and text_offset + i + 2 < len(slus_data):
                        i += 3  # Skip 0xF8 and next 2 bytes
                        continue
                    char = self.char_map.get(byte, f"?[{hex(byte)}]")
                    name += char
                    i += 1
            except IndexError:
                print(f"Invalid text offset {hex(text_offset)} for type {type_id}, reached end of SLUS data")
                name = f"Unknown Type {type_id}"

            name = name.strip().title() if name else f"Unknown Type {type_id}"
            self.card_types_map[type_id] = name
            #print(f"Type {type_id}: {name} at offset {hex(text_offset)}")

        # Load Guardian Stars with multiple 0xF8 prefix handling
        self.guardian_stars_map = {}
        pointer_base += num_type_pointers * 2  # Move to Guardian Star pointers
        #print(f"Loading Guardian Star names using pointers at {hex(pointer_base)}")
        for gs_id in range(num_guardian_star_pointers):
            pointer_offset = pointer_base + (gs_id * 2)
            if pointer_offset + 2 > len(slus_data):
                print(f"Reached end of SLUS data at guardian star pointer {gs_id}")
                break

            pointer_value = int.from_bytes(slus_data[pointer_offset:pointer_offset + 2], 'little')
            text_offset = text_base + pointer_value
            #print(f"Guardian Star {gs_id}: Pointer offset = {hex(pointer_offset)}, Pointer value = {hex(pointer_value)}, Text offset = {hex(text_offset)}")

            # Read the name at the text offset, skipping multiple 0xF8 prefixes if present
            name = ""
            i = 0
            try:
                while i < max_length:
                    if text_offset + i >= len(slus_data):
                        break
                    byte = slus_data[text_offset + i]
                    if byte == 0xFF:
                        #print(f"Found FF terminator at {hex(text_offset + i)} for guardian star {gs_id}")
                        break
                    elif byte == 0xF8 and i + 2 < max_length and text_offset + i + 2 < len(slus_data):
                        i += 3  # Skip 0xF8 and next 2 bytes
                        continue
                    char = self.char_map.get(byte, f"?[{hex(byte)}]")
                    name += char
                    i += 1
            except IndexError:
                print(f"Invalid text offset {hex(text_offset)} for guardian star {gs_id}, reached end of SLUS data")
                name = f"Unknown Guardian Star {gs_id}"

            name = name.strip().title() if name else f"Unknown Guardian Star {gs_id}"
            self.guardian_stars_map[gs_id + 1] = name  # Shifted IDs (1-10)
            #print(f"Guardian Star {gs_id}: {name} at offset {hex(text_offset)}")

        pointer_base += num_guardian_star_pointers * 2
        print(f"Skipping unused pointers at {hex(pointer_base)} (6 bytes)")


    def load_card_names(self, slus_data):
        self.card_names.clear()
        pointer_base = 0x1C6000  # Updated as per user fix
        max_length = 100

        #print(f"Using pointer base: {hex(pointer_base)}")
        card_id = 1
        pointer_offset = 2  # Skip the first pointer as a placeholder

        while card_id <= self.total_cards:
            idx = pointer_base + pointer_offset
            if idx + 1 >= len(slus_data):
                #print(f"Pointer offset {hex(idx)} exceeds SLUS data length {hex(len(slus_data))}")
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
        """Load card descriptions from SLUS data using pointers."""
        self.card_descriptions.clear()
        pointer_base = self.game_info_offsets["card_desc_pointers_start"]
        text_base = self.game_info_offsets["card_desc_text_base"]
        max_length = 200

        #print(f"Using pointer base: {hex(pointer_base)}, text base: {hex(text_base)}")
        card_id = 1
        pointer_offset = 2  # Start at 0x1B0A02

        while card_id <= self.total_cards:
            idx = pointer_base + pointer_offset
            if idx + 1 >= len(slus_data):
                print(f"Pointer offset {hex(idx)} exceeds SLUS data length {hex(len(slus_data))}")
                break
            pointer_bytes = slus_data[idx:idx + 2]
            pointer_little = int.from_bytes(pointer_bytes, 'little')
            pointer_big = int.from_bytes(pointer_bytes, 'big')
            
            pointer = pointer_little
            text_offset = text_base + pointer
            #print(f"Card {card_id}: Pointer offset = {hex(idx)}, Text offset = {hex(text_offset)}")
            
            desc = ""
            i = 0
            try:
                while i < max_length:
                    if text_offset + i >= len(slus_data):
                        break
                    byte = slus_data[text_offset + i]
                    if byte == 0xFF:
                        #print(f"Found FF terminator at {hex(text_offset + i)} for card {card_id} description")
                        break
                    # Special conversions before skipping
                    if byte == 0xF8 and (i + 7) < max_length and text_offset + i + 7 < len(slus_data):
                        seq = slus_data[text_offset + i:text_offset + i + 8]
                        # Match the longer sequence: F8 0B FC 4C F8 0B D5 FE F8 0B FC 5B F8 0B D F8 0B FC 4C F8 0B D5 FE F8 0B FC 5B F8 0B D
                        # Handle "Increase the power of" sequence (length 15)
                        if seq[:15] == bytes([0xF8, 0x0B, 0xFC, 0x4C, 0xF8, 0x0B, 0xD5, 0xFE, 0xF8, 0x0B, 0xFC, 0x5B, 0xF8, 0x0B, 0xD5]):
                            desc += "Increase the power of "
                            i += 15
                            continue
                        # Handle "when Summoned" sequence (length 20)
                        elif seq[:20] == bytes([0xF8, 0x0A, 0x01, 0x00, 0x41, 0x38, 0x38, 0xF8, 0x0A, 0x00, 0x00, 0xFE, 0xF8, 0x0B, 0xFC, 0xF8, 0x0B, 0xD0, 0xF8, 0x0B, 0xD4]):
                            desc += "when summoned"
                            i += 20
                            continue
                    if byte in (0xF8, 0xD5, 0xFC) and i + 1 < max_length and text_offset + i + 1 < len(slus_data):
                        # Skip remaining control codes and next byte (parameter)
                        i += 2
                        continue
                    if byte == 0xFE:
                        prev_byte = slus_data[text_offset + i - 1] if i > 0 else 0x00
                        next_byte = slus_data[text_offset + i + 1] if (text_offset + i + 1) < len(slus_data) else 0x00
                        if prev_byte != 0x00 and next_byte != 0x00:
                            desc += " "
                        i += 1
                        continue
                    # Special case for liNUMBERl, leWORDl, loPHRASEl after F8 conversions
                    if byte == 0xFC and (i + 2) < max_length and text_offset + i + 2 < len(slus_data):
                        next1 = slus_data[text_offset + i + 1]
                        next2 = slus_data[text_offset + i + 2]
                        if next1 == 0xD5:
                            j = i + 3
                            buffer = ""
                            while j < max_length and text_offset + j < len(slus_data):
                                next_byte = slus_data[text_offset + j]
                                if next_byte == 0x6C:  # 'l' character
                                    if buffer.startswith("li") and buffer[2:].isdigit():
                                        desc += buffer[2:-1]  # Number from liNUMBERl
                                    elif buffer.startswith("le") and buffer[2:-1].isalpha():
                                        desc += buffer[2:-1]  # Word from leWORDl
                                    elif buffer.startswith("lo") and buffer[2:-1]:
                                        desc += buffer[2:-1]  # Phrase from loPHRASEl
                                    i = j + 1
                                    break
                                char = self.char_map.get(next_byte, f"?[{hex(next_byte)}]")
                                buffer += char
                                j += 1
                            if i == j:  # No 'l' found, revert
                                i += 3
                                continue
                            continue
                    char = self.char_map.get(byte, f"?[{hex(byte)}]")
                    desc += char
                    i += 1
            except IndexError:
                print(f"Invalid text offset {hex(text_offset)} for card {card_id} description, data may be outside SLUS")
                desc = f"Unknown_{card_id}"
                card_id += 1
                pointer_offset += 2
                continue
            
            # Post-process corrections
            desc = desc.replace("388", "300")  # Correct data error
            desc = desc.replace("bye", "by")   # Fix mapping misread
            desc = desc.strip() if desc else f"Unknown_{card_id}"
            self.card_descriptions[card_id] = desc
            print(f"Card {card_id}: {desc}")

            card_id += 1
            pointer_offset += 2

        print(f"Loaded {len(self.card_descriptions)} card descriptions from SLUS file")

    def load_card_stats(self, slus_data):
        """Load card ATK, DEF, Type, Guard Stars, and Attribute from SLUS_014.11."""
        self.card_stats.clear()
        offset_stats = 0x1C4A42
        offset_levels = 0x1C5B33
        bytes_per_card_stats = 4
        bytes_per_level = 1

        print(f"Loading card stats starting at offset {hex(offset_stats)} and levels at {hex(offset_levels)}")
        for card_id in range(1, self.total_cards + 1):
            # Load ATK/DEF/Type/Guard Stars
            idx_stats = offset_stats + (card_id - 1) * bytes_per_card_stats
            if idx_stats + bytes_per_card_stats > len(slus_data):
                print(f"Reached end of SLUS data at {card_id}")
                break

            # Use bytes 2-5 for stats (4 bytes: a4f10402 for Card 1)
            data_stats = int.from_bytes(slus_data[idx_stats + 2:idx_stats + 6], 'little')
            # Parse ATK (bits 16-24)
            atk_value = ((data_stats) & 0x1FF) * 10
            # Parse DEF (bits 7-15)
            def_value = ((data_stats >> 9) & 0x1FF) * 10
            # Parse Guardian Star 2 (bits 19-22)
            guard_star_2_id = ((data_stats >> 18) & 0xF)
            guard_star_2 = self.guardian_stars_map.get(guard_star_2_id, f"Unknown GS ({guard_star_2_id})")
            # Parse Guardian Star 1 (bits 23-26)
            guard_star_1_id = ((data_stats >> 22) & 0xF)
            guard_star_1 = self.guardian_stars_map.get(guard_star_1_id, f"Unknown GS ({guard_star_1_id})")
            # Parse Type (bits 27-31)
            type_id = ((data_stats >> 26) & 0x1F)
            type_name = self.card_types_map.get(type_id, f"Unknown Type ({type_id})")

            # Load Level and Attribute
            idx_level = offset_levels + ((card_id - 1) * bytes_per_level)
            if idx_level + bytes_per_level > len(slus_data):
                print(f"Reached end of SLUS data at card {card_id} (levels). Expected 1 byte.")
                break
            data_level = slus_data[idx_level]
            level = data_level & 0x0F  # Lower nibble
            attribute_id = (data_level >> 4) & 0xF  # Upper nibble
            attribute_name = self.card_attributes_map.get(attribute_id, f"Unknown Attribute ({hex(attribute_id)})")

            # Store the data
            self.card_stats[card_id] = {
                "atk": atk_value,
                "def": def_value,
                "type": type_name,
                "guard_star_1": guard_star_1,
                "guard_star_2": guard_star_2,
                "attribute": attribute_name,
                "level": level
            }

            # Debug print for specific cards
            if card_id in [1, 722]:
                print(f"Card {card_id}: ATK = {atk_value}, DEF = {def_value}, Type = {type_name}, "
                      f"Guard Star 1 = {guard_star_1}, Guard Star 2 = {guard_star_2}, "
                      f"Attribute = {attribute_name}, Level = {level}, "
                      f"Bytes (stats) = {binascii.hexlify(slus_data[idx_stats:idx_stats + 6])}, "
                      f"Bytes (level) = {binascii.hexlify(bytes([data_level]))}")

        print(f"Loaded stats for {len(self.card_stats)} cards from SLUS file")
    
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
        if not self.iso_path:
            messagebox.showerror("Error", "Please select an ISO file first.")
            return
    
        patch_window = tk.Toplevel(self.root)
        patch_window.title("Patch ISO")
        patch_window.geometry("400x500")
    
        # Drop rate selection
        tk.Label(patch_window, text="Select Drop Rate:", font=("Arial", 10, "bold")).pack(pady=10)
        self.drop_rate_var = tk.StringVar(value="100")  # Default to 100
        drop_rate_frame = tk.Frame(patch_window)
        drop_rate_frame.pack(pady=5)
        tk.Radiobutton(drop_rate_frame, text="100 Drops", variable=self.drop_rate_var, value="100").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(drop_rate_frame, text="1000 Drops", variable=self.drop_rate_var, value="1000").pack(side=tk.LEFT, padx=5)
    
        # Patch selection checkboxes
        tk.Label(patch_window, text="Select Patches to Apply:", font=("Arial", 10, "bold")).pack(pady=10)
        self.patch_vars = {}
        patches = [
            ("Drop Rate", "drop_rate"),
            ("Exodia S-Tec", "exodia"),
            ("No Password Limit", "password"),
            ("Starchips", "starchips"),
            ("Win Requirements", "win_requirements"),
        ]
        for patch_name, patch_key in patches:
            self.patch_vars[patch_key] = tk.BooleanVar()
            frame = tk.Frame(patch_window)
            frame.pack(fill=tk.X, padx=10)
            tk.Checkbutton(frame, text=f"Enable {patch_name}", variable=self.patch_vars[patch_key]).pack(side=tk.LEFT)
            tk.Checkbutton(frame, text=f"Disable {patch_name}", variable=self.patch_vars[patch_key], onvalue=False, offvalue=True).pack(side=tk.LEFT)
    
        # Button frame
        button_frame = tk.Frame(patch_window)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Check and Patch ISO", command=self.apply_patches, bg="green", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Reverse Patches", command=self.reverse_patches, bg="red", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="View Opponents", command=self.show_view_data_interface, bg="blue", fg="white").pack(side=tk.LEFT, padx=5)

    def apply_patches(self):
        self.applied_patches.clear()
        self.check_and_patch_iso()  # Delegate to the full method

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
        # Set default to the second opponent (index 1) if available, otherwise empty
        default_opponent = self.opponents[1] if len(self.opponents) > 1 else ""
        self.selected_opponent.set(default_opponent)
        opponent_menu = ttk.OptionMenu(view_window, self.selected_opponent, None, *self.opponents, command=self.load_opponent_data_view)
        # Disable the first opponent (index 0, e.g., "Build Deck" or "Duel Master K")
        if self.opponents and self.opponents[0] in ["Build Deck", "Duel Master K"]:
            opponent_menu['menu'].entryconfig(0, state="disabled")
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

        # Load initial data
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
        """Set up a Treeview table with an integrated scrollbar for the 'All Cards' view."""
        # Create a frame to hold the Treeview and Scrollbar
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Card ID", "Card Name", "ATK/DEF", "Description")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        tree.heading("Card ID", text="Card ID")
        tree.heading("Card Name", text="Card Name")
        tree.heading("ATK/DEF", text="ATK/DEF")
        tree.heading("Description", text="Description")
        tree.column("Card ID", width=60)
        tree.column("Card Name", width=200)
        tree.column("ATK/DEF", width=100)
        tree.column("Description", width=300)

        # Add vertical scrollbar integrated with the Treeview
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        # Pack the Treeview and Scrollbar
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tree.bind("<<TreeviewSelect>>", lambda event: self.show_card_info(tree, view_name.lower().replace(" ", "_").replace("/", "_")))

        self.all_cards_tree = tree

    def load_card_passwords_and_costs(self):
        """Load card passwords and starchip costs from WA_MRG.MRG at offset 0xFB9808."""
        if not self.wamrg_path:
            print("No WAMRG file loaded. Cannot load card passwords and costs.")
            return

        self.card_passwords_and_costs.clear()
        offset = 0xFB9808
        bytes_per_card = 8

        try:
            with open(self.wamrg_path, 'rb') as f:
                for card_id in range(1, self.total_cards + 1):
                    f.seek(offset + (card_id - 1) * bytes_per_card)
                    data = f.read(bytes_per_card)
                    if len(data) != bytes_per_card:
                        print(f"Reached end of file at card {card_id}. Expected {bytes_per_card} bytes, got {len(data)}.")
                        break

                    # Parse cost (first 4 bytes, little-endian)
                    cost = int.from_bytes(data[0:4], 'little')
                    # Parse code (last 4 bytes, little-endian)
                    code = int.from_bytes(data[4:8], 'little')

                    # Store the data
                    self.card_passwords_and_costs[card_id] = {
                        "cost": cost,
                        "code": "No Password" if code == 0xFFFFFFFE else f"{code:08d}"  # Format as 8-digit string or "No Password"
                    }
                    # Debug print for specific cards
                    #if card_id in [1, 2, 3, 4]:
                        #print(f"Card {card_id}: Cost = {cost} starchips, Code = {self.card_passwords_and_costs[card_id]['code']}, Bytes = {binascii.hexlify(data)}")

        except Exception as e:
            print(f"Failed to load card passwords and costs: {e}")
            traceback.print_exc()

    def add_search_bar(self, frame, tree, data_type):
        """Add a search bar below the Treeview with auto-search and share option."""
        tree.pack(fill=tk.BOTH, expand=True)  # Ensure Treeview is packed first
        search_frame = tk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = tk.Entry(search_frame)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.insert(0, self.search_terms[data_type])  # Load the view-specific search term
        search_entry.bind("<KeyRelease>", lambda event: self.update_search(tree, search_entry, data_type))
        # Add Share Search button
        share_button = tk.Button(search_frame, text="Share Search", command=lambda: self.share_search(data_type))
        share_button.pack(side=tk.RIGHT, padx=5)

    def update_search(self, tree, search_entry, data_type):
        """Update the search text for the specific view and filter the Treeview."""
        self.search_terms[data_type] = search_entry.get()
        self.filter_treeview(tree, self.search_terms[data_type], data_type)

    def share_search(self, data_type):
        """Share the current view's search term with all other views."""
        current_search = self.search_terms[data_type]
        for key in self.search_terms:
            self.search_terms[key] = current_search
        # Update all views with the shared search term
        self.update_all_views()

    def update_all_views(self):
        """Update all Treeview tables with their respective search terms."""
        if hasattr(self, 'deck_tree'):
            self.update_treeview(self.deck_tree, self.opponent_data.get("deck", {}), "deck")
        if hasattr(self, 'sa_pow_tree'):
            self.update_treeview(self.sa_pow_tree, self.opponent_data.get("sa_pow", {}), "sa_pow")
        if hasattr(self, 'bcd_tree'):
            self.update_treeview(self.bcd_tree, self.opponent_data.get("bcd", {}), "bcd")
        if hasattr(self, 'sa_tec_tree'):
            self.update_treeview(self.sa_tec_tree, self.opponent_data.get("sa_tec", {}), "sa_tec")
        if hasattr(self, 'all_cards_tree'):
            self.load_all_cards_view()

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
                # Parse the chance string (e.g., "500/2048") to get the numerator
                try:
                    display_chance = f"{chance}/2048"  # Display as percentage
                except (ValueError, IndexError) as e:
                    print(f"Warning: Failed to parse chance {chance} for card {card_id}, error: {e}")
                    display_chance = "N/A"
                if search_text in str(card_id) or search_text in card_name or search_text in atk_def:
                    tree.insert("", tk.END, values=(card_id, card_name.title(), atk_def, display_chance), tags=(card_id, data_type))

    def load_opponent_names(self, slus_data): 
        self.opponents.clear()
        pointer_base = 0x1C6650
        text_base = 0x1C0800
        expected_opponents = 40
        max_length = 50

        #print(f"Loading opponent names using pointer table at {hex(pointer_base)}")
        temp_opponents = []

        for opponent_id in range(expected_opponents):
            # Read the pointer
            pointer_offset = pointer_base + (opponent_id * 2)
            if pointer_offset + 2 > len(slus_data):
                print(f"Reached end of SLUS data at opponent {opponent_id} while reading pointer.")
                break

            pointer_value = int.from_bytes(slus_data[pointer_offset:pointer_offset + 2], 'little')
            text_offset = text_base + pointer_value
            #print(f"Opponent {opponent_id}: Pointer offset = {hex(pointer_offset)}, Pointer value = {hex(pointer_value)}, Text offset = {hex(text_offset)}")

            # Read the name at the text offset
            name = ""
            i = 0
            try:
                # Skip possible 0xF8 prefix
                if slus_data[text_offset:text_offset + 3] == bytes([0xF8, slus_data[text_offset + 1], slus_data[text_offset + 2]]):
                    i = 3
                    text_offset += 3
                while i < max_length:
                    byte = slus_data[text_offset + i]
                    # Stop at 0xFF (terminator)
                    if byte == 0xFF:
                        break
                    # Stop at 0xFD (start of garbled/extra data)
                    if byte == 0xFD:
                        break
                    char = self.char_map.get(byte, f"?[{hex(byte)}]")
                    name += char
                    i += 1
            except IndexError:
                print(f"Invalid text offset {hex(text_offset)} for opponent {opponent_id}, reached end of SLUS data")
                name = f"Unknown_{opponent_id}"

            name = name.strip().title() if name else f"Unknown_{opponent_id}"
            temp_opponents.append(name)
            #print(f"Opponent {opponent_id}: {name} at offset {hex(text_offset)}, bytes: {binascii.hexlify(slus_data[text_offset:text_offset + i])}")

        # Skip the first opponent to align with 39 opponents with drop data
        self.opponents = temp_opponents
        print(f"Loaded {len(self.opponents)} opponent names from SLUS file after skipping the first entry")
    #
    def load_opponent_data_view(self, event=None):
        """Load opponent data and update the Treeview tables with view-specific search."""
        if not self.wamrg_path or not self.selected_opponent.get():
            return
        opponent_name = self.selected_opponent.get()
        if not opponent_name:
            return

        try:
            opponent_id = self.opponents.index(opponent_name)
            print(f"Loading data for {opponent_name} with ID {opponent_id}")
            with open(self.wamrg_path, 'rb') as f:
                file_size = os.path.getsize(self.wamrg_path)
                print(f"Loading from: {self.wamrg_path}, Size: {file_size} bytes")

                # Check for invalid opponent (e.g., "Build Deck" or "Duel Master K" at index 0)
                if opponent_id == 0:
                    print(f"Opponent {opponent_name} (ID 0) is disabled and has no drop data")
                    self.opponent_data = {"deck": {}, "sa_pow": {}, "bcd": {}, "sa_tec": {}}
                    self.update_treeview(self.deck_tree, {}, "deck")
                    self.update_treeview(self.sa_pow_tree, {}, "sa_pow")
                    self.update_treeview(self.bcd_tree, {}, "bcd")
                    self.update_treeview(self.sa_tec_tree, {}, "sa_tec")
                    return

                # Valid opponents start from index 1
                base_offset = 0xE99800 + (opponent_id * self.opponent_block_size)
                #print(f"Base offset for {opponent_name} (ID {opponent_id}): {hex(base_offset)}")

                # Check if the offset is within file bounds
                max_offset = base_offset + self.opponent_block_size
                if max_offset > file_size:
                    raise ValueError(f"Opponent data for {opponent_name} at offset {hex(base_offset)} exceeds file size {file_size} bytes")

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
        """Load and display all cards in the Treeview table with view-specific search."""
        if not self.all_cards_tree:
            return

        # Clear existing entries
        for item in self.all_cards_tree.get_children():
            self.all_cards_tree.delete(item)

        # Insert all cards based on view-specific search
        self.filter_treeview(self.all_cards_tree, self.search_terms["all_cards"], "all_cards")

    def reverse_lookup_equips(self, wamrg_path): #this is a function to show which equips a card can use
        """Reverse lookup to find all equips a monster (card) can use based on equip data."""
        equip_offsets = {
            0: (0xB85000, 0xB87800),  # No Field
            1: (0xBFA800, 0xBFD000),  # Forest Field
            2: (0xC70000, 0xC72800),  # Wasteland Field
            3: (0xCE5800, 0xCE8000),  # Mountain Field
            4: (0xD5B000, 0xD5D800),  # Sogen Field
            5: (0xDD0800, 0xDD3000),  # Umi Field
            6: (0xE46000, 0xE48800)   # Yami Field
        }
        card_to_equips = {}  # Map card ID to list of (equip_id, equip_name) tuples

        try:
            with open(wamrg_path, 'rb') as f:
                for field_type, (start_offset, end_offset) in equip_offsets.items():
                    current_offset = start_offset
                    while current_offset < end_offset:
                        f.seek(current_offset)
                        # Read equip card ID (2 bytes)
                        equip_id = int.from_bytes(f.read(2), 'little')
                        if equip_id == 0:
                            break  # End of equip data for this field
                        # Read total number of cards (2 bytes)
                        total_cards = int.from_bytes(f.read(2), 'little')
                        # Read the list of material card IDs
                        material_cards = []
                        for _ in range(total_cards):
                            card_id = int.from_bytes(f.read(2), 'little')
                            if card_id != 0:  # Skip null entries
                                material_cards.append(card_id)
                            current_offset += 2
                        current_offset += 4  # Move past equip_id and total_cards

                        # Update reverse lookup with names
                        equip_name = self.card_names.get(equip_id, f"Unknown_{equip_id}")
                        for card_id in material_cards:
                            if card_id not in card_to_equips:
                                card_to_equips[card_id] = []
                            if (equip_id, equip_name) not in card_to_equips[card_id]:
                                card_to_equips[card_id].append((equip_id, equip_name))

            return card_to_equips

        except Exception as e:
            print(f"Error processing equip data: {e}")
            return {}


    def update_treeview(self, tree, chances, data_type):
        """Update the Treeview with the given data and view-specific search."""
        # Clear existing entries
        for item in tree.get_children():
            tree.delete(item)

        # Insert new data based on view-specific search
        self.filter_treeview(tree, self.search_terms[data_type], data_type)

    def show_card_info(self, tree, data_type):
        """Display card info when a card is clicked."""
        selected_item = tree.selection()
        if not selected_item:
            return
        card_id = int(tree.item(selected_item)["values"][0])
        
        card_name = self.card_names.get(card_id, f"Unknown_{card_id}")
        card_desc = self.card_descriptions.get(card_id, "No description available")
        stats = self.card_stats.get(card_id, {"atk": "N/A", "def": "N/A", "type": "N/A", "level": "N/A", "guard_star_1": "N/A", "guard_star_2": "N/A", "attribute": "N/A"})
        atk_def = f"{stats['atk']}/{stats['def']}"
        card_type = stats.get("type", "normal")
        card_level = stats.get("level", "N/A")
        guard_star_1 = stats.get("guard_star_1", "N/A")
        guard_star_2 = stats.get("guard_star_2", "N/A")
        card_attribute = stats.get("attribute", "N/A")


        password_cost = self.card_passwords_and_costs.get(card_id, {"cost": "N/A", "code": "No Password"})
        card_cost = password_cost["cost"]
        card_password = password_cost["code"]

        droppers = self.card_droppers.get(card_id, {"sa_pow": [], "bcd": [], "sa_tec": []})
        sa_pow_droppers = "\n".join([f"{opp}: {chance}/2048" for opp, chance in droppers["sa_pow"]]) or "None"
        bcd_droppers = "\n".join([f"{opp}: {chance}/2048" for opp, chance in droppers["bcd"]]) or "None"
        sa_tec_droppers = "\n".join([f"{opp}: {chance}/2048" for opp, chance in droppers["sa_tec"]]) or "None"

        #Get equipable cards for this card
        compatible_equips = self.card_to_equips.get(card_id, [])
        if compatible_equips:
            equip_list = ", ".join(f"{equip_id} ({equip_name})" for equip_id, equip_name in compatible_equips
        ) 
        else:
            equip_list = "None"



        info_text = (
            f"Card ID: {card_id}\n"
            f"Name: {card_name}\n"
            f"Type: {card_type}\n"
            f"Level: {card_level}\n"
            f"Guardian Star 1: {guard_star_1}\n"
            f"Guardian Star 2: {guard_star_2}\n"
            f"Attribute: {card_attribute}\n"
            f"ATK/DEF: {atk_def}\n"
            f"Description: {card_desc}\n\n"
            f"Password: {card_password}\n"
            f"Cost: {card_cost} starchips\n\n"
            f"Dropped by (S/A POW):\n{sa_pow_droppers}\n\n"
            f"Dropped by (B/C/D):\n{bcd_droppers}\n\n"
            f"Dropped by (S/A TEC):\n{sa_tec_droppers}\n"
            f"Equipable Cards: {equip_list}\n"
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

    def parse_drop_chances(self, data, drop_type): ##this function loads all opponent's drop chances from the WAMRG file when you view a specific card's data
        """Parse drop chances from raw data into a dictionary of card_id: chance."""
        chances = {}
        expected_entries = self.total_cards  # Assuming one chance per card
        max_data_size = expected_entries * 2  # 2 bytes per chance

        if len(data) != max_data_size:
            print(f"Warning: {drop_type} data length {len(data)} does not match expected {max_data_size} bytes for {expected_entries} cards")

        for card_id in range(1, self.total_cards + 1):
            idx = (card_id - 1) * 2
            if idx + 2 > len(data):
                print(f"Warning: Incomplete data for card {card_id} in {drop_type} at index {idx}")
                break
            chance_raw = int.from_bytes(data[idx:idx + 2], 'little')
            # Normalize chance to 0-2048 range
            chance = min(chance_raw, 2048)
            if chance_raw > 2048:
                print(f"Warning: Invalid chance {chance_raw} for card {card_id} in {drop_type}, capped to {chance}")
            if chance > 0:
                chances[card_id] = f"{chance}"  # Single fraction format

        return chances


    def get_card_image_path(self, card_id):
        card_type = self.card_types.get(card_id, "normal")
        image_name = self.card_image_map.get(card_type, self.card_image_map["base"])
        return os.path.join(self.image_base_path, f"{image_name}.png")


if __name__ == "__main__":
    root = tk.Tk()
    app = YGOISOPatcher(root)
    root.mainloop()
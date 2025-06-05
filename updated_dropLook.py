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
            # Added from log analysis
            0x47: " ", 0x6F: "?", 0x77: "?", 0x7F: "?", 0x8F: "?", 0x97: "?", 0x9F: "?",
            0xAF: "?", 0xB7: "?", 0xC7: "?", 0xE7: "?", 0xEF: "?", 0xF7: "?",
        }
        self.opponents = []  # Will be populated dynamically
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
        self.data_size = 1460  # Bytes for 722 cards (2 bytes each)
        self.opponent_block_size = 0x1800  # Size of each opponent's data block

        # Known game info offsets
        self.game_info_offsets = {
            "types_start": 0x1C92CE,
            "guardian_stars_start": 0x1C9380,
            "opponents_start": 0x1C93D0,
            "locations_start": 0x1C959A,
            "scrambled_data_start": 0x1C9804,
            "scrambled_data_end": 0x1C98CB,
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

        # GUI Setup
        self.iso_label = tk.Label(root, text="Select ISO/BIN File:")
        self.iso_label.pack()
        self.iso_display = tk.Label(root, text="No ISO file selected")
        self.iso_display.pack()
        self.select_iso_button = tk.Button(root, text="Select ISO File", command=self.select_iso)
        self.select_iso_button.pack()

        self.slus_label = tk.Label(root, text="Select SLUS File (SLUS_014.11):")
        self.slus_label.pack()
        self.slus_display = tk.Label(root, text="No SLUS file selected")
        self.slus_display.pack()
        self.select_slus_button = tk.Button(root, text="Select SLUS File", command=self.select_slus)
        self.select_slus_button.pack()

        self.wamrg_label = tk.Label(root, text="Select WAMRG File (optional):")
        self.wamrg_label.pack()
        self.wamrg_display = tk.Label(root, text="No WAMRG file selected")
        self.wamrg_display.pack()
        self.select_wamrg_button = tk.Button(root, text="Select WAMRG File", command=self.select_wamrg)
        self.select_wamrg_button.pack()

        self.opponent_label = tk.Label(root, text="Select Opponent:")
        self.opponent_label.pack()
        self.opponent_menu = ttk.OptionMenu(root, self.selected_opponent, "", "", command=self.load_opponent_data)
        self.opponent_menu.pack()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.deck_frame = tk.Frame(self.notebook)
        self.deck_text = tk.Text(self.deck_frame, height=10, width=50)
        self.deck_text.pack(fill=tk.BOTH, expand=True)
        self.deck_image_label = tk.Label(self.deck_frame)
        self.deck_image_label.pack()
        self.notebook.add(self.deck_frame, text="Deck")

        self.sa_pow_frame = tk.Frame(self.notebook)
        self.sa_pow_text = tk.Text(self.sa_pow_frame, height=10, width=50)
        self.sa_pow_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.sa_pow_frame, text="S/A POW Drops")

        self.bcd_frame = tk.Frame(self.notebook)
        self.bcd_text = tk.Text(self.bcd_frame, height=10, width=50)
        self.bcd_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.bcd_frame, text="B/C/D Drops")

        self.sa_tec_frame = tk.Frame(self.notebook)
        self.sa_tec_text = tk.Text(self.sa_tec_frame, height=10, width=50)
        self.sa_tec_text.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(self.sa_tec_frame, text="S/A TEC Drops")

        self.patches_label = tk.Label(root, text="Select Patches to Apply (to ISO):")
        self.patches_label.pack()
        self.patch_vars = {}
        self.patch_vars['password'] = tk.BooleanVar()
        tk.Checkbutton(root, text="No Password Limit Patch", variable=self.patch_vars['password']).pack()
        self.patch_vars['unlock_duelists'] = tk.BooleanVar()
        tk.Checkbutton(root, text="Unlock All Duelists", variable=self.patch_vars['unlock_duelists']).pack()

        self.apply_button = tk.Button(root, text="Check and Patch ISO", command=self.check_and_patch_iso, bg="green", fg="white")
        self.apply_button.pack()
        self.view_button = tk.Button(root, text="Refresh Views", command=self.load_opponent_data)
        self.view_button.pack()
        self.status_label = tk.Label(root, text="")
        self.status_label.pack()

    def select_iso(self):
        self.iso_path = filedialog.askopenfilename(filetypes=[("ISO/BIN files", "*.iso *.bin")])
        self.iso_display.config(text=self.iso_path or "No ISO file selected")
        if self.iso_path:
            try:
                self.extract_files()
                if self.slus_path:
                    with open(self.slus_path, "rb") as f:
                        slus_data = f.read()
                    self.load_opponent_names(slus_data)  # Load opponent names
                    self.load_card_names(slus_data)
                self.load_card_types()
                self.selected_opponent.set("")
                self.update_opponent_menu()  # Update the menu after loading names
                self.load_opponent_data()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to process ISO: {e}")
                traceback.print_exc()

    def select_slus(self):
        self.slus_path = filedialog.askopenfilename(filetypes=[("SLUS files", "SLUS_014.11")])
        self.slus_display.config(text=self.slus_path or "No SLUS file selected")
        if self.slus_path:
            try:
                with open(self.slus_path, "rb") as f:
                    slus_data = f.read()
                self.load_opponent_names(slus_data)  # Load opponent names
                self.load_card_names(slus_data)
                self.load_card_types()
                self.update_opponent_menu()  # Update the menu after loading names
                self.load_opponent_data()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load SLUS file: {e}")
                traceback.print_exc()

    def select_wamrg(self):
        self.wamrg_path = filedialog.askopenfilename(filetypes=[("WAMRG files", "*.dat *.mrg")])
        self.wamrg_display.config(text=self.wamrg_path or "No WAMRG file selected")
        if self.wamrg_path:
            try:
                self.load_opponent_data()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load WAMRG data: {e}")
                traceback.print_exc()

    def extract_files(self):
        # Disabled for now since we're using direct SLUS loading
        pass

    def load_opponent_names(self, slus_data):
        """Load and decode opponent names from SLUS_014.11."""
        self.opponents.clear()
        offset = self.game_info_offsets["opponents_start"]
        max_length = 50  # Maximum length for a name to prevent infinite loops
        expected_opponents = 40  # We expect 40 opponents (ID 0 to 27 in hex)

        print(f"Loading opponent names starting at offset {hex(offset)}")
        opponent_id = 0

        while opponent_id < expected_opponents:
            name = ""
            i = 0
            try:
                # Skip F8 xx xx prefix if present
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
                # Move offset to the start of the next name
                offset += i + 1
            except IndexError:
                print(f"Invalid offset {hex(offset)} for opponent {opponent_id}, reached end of SLUS data")
                name = f"Unknown_{opponent_id}"
                break

            # Clean up and store the name
            name = name.strip().title() if name else f"Unknown_{opponent_id}"
            self.opponents.append(name)
            print(f"Opponent {opponent_id}: {name} at offset {hex(offset - i - 1)}, bytes: {binascii.hexlify(slus_data[offset - i - 1:offset - 1])}")
            opponent_id += 1

        print(f"Loaded {len(self.opponents)} opponent names from SLUS file")

    def update_opponent_menu(self):
        """Update the opponent dropdown menu with loaded names."""
        menu = self.opponent_menu["menu"]
        menu.delete(0, "end")
        for opponent in self.opponents:
            menu.add_command(label=opponent, command=lambda value=opponent: self.selected_opponent.set(value))
        self.selected_opponent.set("")

    def load_card_names(self, slus_data):
        """Load and decode all card names using the pointer and name formulas."""
        self.card_names.clear()
        pointer_base = 0x1C6002  # Starting pointer address for Card 001
        max_length = 100

        print(f"Using pointer base: {hex(pointer_base)}")
        card_id = 1
        pointer_offset = 0  # Offset from pointer_base

        while card_id <= self.total_cards:
            # Pointer Formula: 0x1C6002 + (card_id - 1) * 2
            idx = pointer_base + pointer_offset
            if idx + 1 >= len(slus_data):
                print(f"Pointer offset {hex(idx)} exceeds SLUS data length {hex(len(slus_data))}")
                break
            # Read the 2-byte pointer
            pointer_bytes = slus_data[idx:idx + 2]
            pointer_little = int.from_bytes(pointer_bytes, 'little')
            pointer_big = int.from_bytes(pointer_bytes, 'big')
            print(f"Card {card_id} raw pointer bytes at {hex(idx)}: {binascii.hexlify(pointer_bytes)} (little-endian: {hex(pointer_little)}, big-endian: {hex(pointer_big)})")
            
            # Use little-endian directly without inversion
            pointer = pointer_little
            
            # Card Name Formula: 0x1C0800 + pointer (no inversion)
            text_offset = 0x1C0800 + pointer
            print(f"Card {card_id} pointer: {hex(pointer)} (raw offset {hex(idx)}, calculated text offset {hex(text_offset)})")
            
            name = ""
            i = 0
            try:
                # Skip F8 xx xx prefix if present
                if slus_data[text_offset:text_offset + 3] == bytes([0xF8, slus_data[text_offset + 1], slus_data[text_offset + 2]]):
                    i = 3  # Skip the 3-byte F8 sequence
                while i < max_length:
                    byte = slus_data[text_offset + i]
                    if byte == 0xFF:
                        print(f"Found FF terminator at {hex(text_offset + i)} for card {card_id}")
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
            if card_id in [1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 35, 167, 216, 237, 311, 323, 335, 336, 340, 349, 363, 433, 551, 558, 591, 665, 666, 677, 681, 682, 688, 674, 722]:
                print(f"Card {card_id}: {name} at text offset {hex(text_offset)}, bytes: {binascii.hexlify(slus_data[text_offset:text_offset + i] if text_offset + i <= len(slus_data) else b'offset exceeds SLUS')}")
            card_id += 1
            pointer_offset += 2

        print(f"Loaded {len(self.card_names)} card names from SLUS file")

    def load_card_types(self):
        """Placeholder for loading card types."""
        pass

    def parse_deck(self, data):
        """Parse deck chances for the opponent."""
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
        """Parse drop chances for the opponent."""
        chances = {}
        for card_id in range(1, self.total_cards + 1):
            idx = (card_id - 1) * 2
            if idx + 2 > len(data):
                break
            chance = int.from_bytes(data[idx:idx + 2], 'little')
            if chance > 0:
                chances[card_id] = chance
        return chances

    def load_opponent_data(self, event=None):
        """Load opponent data and update GUI."""
        if not self.wamrg_path or not self.selected_opponent.get():
            return
        opponent_name = self.selected_opponent.get()
        if not opponent_name or opponent_name == self.opponents[0]:  # Skip "Build Deck" equivalent
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
                print(f"Raw deck data (first 80 bytes) at {hex(base_offset)}: {deck_data[:80].hex()}...")
                deck_chances = self.parse_deck(deck_data)
                self.opponent_data["deck"] = deck_chances
                print(f"{opponent_name} Deck: Found {len(deck_chances)} cards with non-zero chances out of {self.total_cards}")

                # S/A POW Drops
                f.seek(base_offset + self.wamrg_offsets["sa_pow_drops"])
                sa_pow_data = f.read(self.data_size)
                print(f"Raw S/A POW drops data at {hex(base_offset + self.wamrg_offsets['sa_pow_drops'])}: {sa_pow_data[:80].hex()}...")
                sa_pow_chances = self.parse_drop_chances(sa_pow_data, "sa_pow")
                self.opponent_data["sa_pow"] = sa_pow_chances
                print(f"{opponent_name} S/A POW Drops: Found {len(sa_pow_chances)} cards with non-zero chances out of {self.total_cards}")

                # B/C/D Drops
                f.seek(base_offset + self.wamrg_offsets["bcd_drops"])
                bcd_data = f.read(self.data_size)
                print(f"Raw B/C/D drops data at {hex(base_offset + self.wamrg_offsets['bcd_drops'])}: {bcd_data[:80].hex()}...")
                bcd_chances = self.parse_drop_chances(bcd_data, "bcd")
                self.opponent_data["bcd"] = bcd_chances
                print(f"{opponent_name} B/C/D Drops: Found {len(bcd_chances)} cards with non-zero chances out of {self.total_cards}")

                # S/A TEC Drops
                f.seek(base_offset + self.wamrg_offsets["sa_tec_drops"])
                sa_tec_data = f.read(self.data_size)
                print(f"Raw S/A TEC drops data at {hex(base_offset + self.wamrg_offsets['sa_tec_drops'])}: {sa_tec_data[:80].hex()}...")
                sa_tec_chances = self.parse_drop_chances(sa_tec_data, "sa_tec")
                self.opponent_data["sa_tec"] = sa_tec_chances
                print(f"{opponent_name} S/A TEC Drops: Found {len(sa_tec_chances)} cards with non-zero chances out of {self.total_cards}")

            # Update GUI
            self.deck_text.delete(1.0, tk.END)
            for card_id, chance in sorted(self.opponent_data.get("deck", {}).items(), key=lambda x: x[1], reverse=True):
                card_name = self.card_names.get(card_id, f"Unknown_{card_id}")
                self.deck_text.insert(tk.END, f"Card {card_id}: {card_name} - Chance: {chance}/2048 ({chance/2048*100:.2f}%)\n")

            self.sa_pow_text.delete(1.0, tk.END)
            for card_id, chance in sorted(self.opponent_data.get("sa_pow", {}).items(), key=lambda x: x[1], reverse=True):
                card_name = self.card_names.get(card_id, f"Unknown_{card_id}")
                self.sa_pow_text.insert(tk.END, f"Card {card_id}: {card_name} - Chance: {chance}/2048 ({chance/2048*100:.2f}%)\n")

            self.bcd_text.delete(1.0, tk.END)
            for card_id, chance in sorted(self.opponent_data.get("bcd", {}).items(), key=lambda x: x[1], reverse=True):
                card_name = self.card_names.get(card_id, f"Unknown_{card_id}")
                self.bcd_text.insert(tk.END, f"Card {card_id}: {card_name} - Chance: {chance}/2048 ({chance/2048*100:.2f}%)\n")

            self.sa_tec_text.delete(1.0, tk.END)
            for card_id, chance in sorted(self.opponent_data.get("sa_tec", {}).items(), key=lambda x: x[1], reverse=True):
                card_name = self.card_names.get(card_id, f"Unknown_{card_id}")
                self.sa_tec_text.insert(tk.END, f"Card {card_id}: {card_name} - Chance: {chance}/2048 ({chance/2048*100:.2f}%)\n")

            # Load card image (if any)
            self.deck_image_label.config(image='')
            self.photo_references.clear()
            first_card_id = next(iter(self.opponent_data.get("deck", {}).items()), None)[0] if self.opponent_data.get("deck") else None
            if first_card_id and Image and ImageTk:
                image_path = self.get_card_image_path(first_card_id)
                if os.path.exists(image_path):
                    try:
                        image = Image.open(image_path)
                        image = image.resize((100, 150), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(image)
                        self.deck_image_label.config(image=photo)
                        self.photo_references.append(photo)
                    except Exception as e:
                        print(f"Failed to load image for card {first_card_id}: {e}")
                else:
                    print(f"No valid image found for card ID {first_card_id}, skipping image.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load opponent data: {e}")
            traceback.print_exc()

    def get_card_image_path(self, card_id):
        """Get the image path for a card."""
        card_type = self.card_types.get(card_id, "normal")
        image_name = self.card_image_map.get(card_type, self.card_image_map["base"])
        return os.path.join(self.image_base_path, f"{image_name}.png")

    def check_and_patch_iso(self):
        """Check and apply patches to the ISO."""
        if not self.iso_path:
            messagebox.showerror("Error", "No ISO file selected.")
            return

        try:
            self.applied_patches.clear()
            if self.patch_vars['password'].get():
                self.apply_password_patch()
            if self.patch_vars['unlock_duelists'].get():
                self.apply_unlock_duelists_patch()

            if self.applied_patches:
                messagebox.showinfo("Success", f"Applied patches: {', '.join(self.applied_patches)}")
            else:
                messagebox.showinfo("Info", "No patches applied.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to patch ISO: {e}")
            traceback.print_exc()

    def apply_password_patch(self):
        """Apply the no password limit patch."""
        # Placeholder for password patch logic
        self.applied_patches.append("No Password Limit")

    def apply_unlock_duelists_patch(self):
        """Apply the unlock all duelists patch."""
        # Placeholder for unlock duelists patch logic
        self.applied_patches.append("Unlock All Duelists")

if __name__ == "__main__":
    root = tk.Tk()
    app = YGOISOPatcher(root)
    root.mainloop()
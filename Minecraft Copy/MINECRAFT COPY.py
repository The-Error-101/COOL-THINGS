"""A small Minecraft-inspired severity scanner game."""

"""
EDITING GUIDE
=============
Use the fold arrows beside each ``# region`` to work on one system at a time.

SAFE EDITING RULES
------------------
1. Change constants in ``Game rules and content`` without changing method code.
2. Change player position, movement speed, and turning in ``Player state and camera``.
3. Change item names, counts, pickup, and placement in ``Inventory and items``.
4. Change world storage only in ``World data and save/load``. Keep old save keys
    compatible unless you also update ``load_selected_world``.
5. Change visuals in ``3D rendering and block interaction``. Keep severity values
    in ``self.blocks`` hidden from the renderer; scoring reads them internally.
6. Change commands only in ``Command blocks`` or ``Admin commands and audit logs``.
7. After every edit, run: ``python -m py_compile file.py``.
8. Account records, roles, and permissions are separate sections below. Change
    one area at a time and keep the account name as the dictionary key.

IMPORTANT STATE MAP
-------------------
``self.blocks``          Hidden severity values for each world cell.
``self.mined_blocks``    Cells opened by the player; these become walkable.
``self.block_materials`` Visible material names used by the 3D renderer.
``self.inventory``       Item name to quantity mapping.
``self.selected_item``   Item currently selected for placement.
``self.player_x/y``      Player position in world coordinates.
``self.player_angle``    Camera direction in radians.
``self.current_value``   The hidden severity value currently being scored.

To add a new item: add its name to ``RANDOM_THINGS``. To add a placeable block,
add a starting count to ``self.inventory`` and a color in ``wall_color``.
To add a role, add one entry to ``ROLE_RANK``. Higher rank automatically inherits
lower-rank commands. To make an account in one line, call
``account_store.create_account("Name", "Password", "role")``.
To add a command, update the command tuple and its executor together.
"""

import random
import hashlib
import json
import math
import re
import secrets
import shlex
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


# region Game rules and content

SEVERITY_MESSAGES: dict[int | None, str] = {
    None: "unknown or not applicable",
    0: "informational",
    1: "normal",
    2: "warning",
    3: "problem detected",
    4: "potential error",
    5: "emergency",
    6: "error",
    7: "high error",
    8: "major error",
    9: "critical error",
}

# region Roles and permission definitions

# QUICK EDIT AREA: player defaults, roles, and permissions
DEFAULT_PLAYER_ROLE = "user"
PLAYER_START_X = 2.5
PLAYER_START_Y = 2.5
PLAYER_START_ANGLE = 0.0
# Roles are ordered. Every user rank has 100 more capabilities than the rank before it.
ROLE_RANK = {
    "banned": -1, "user": 0, "mod": 1, "op": 2, "superop": 3,
    "headadmin": 4, "co-owner": 5, "owner": 6,
}
USER_RANKS = [f"user-rank-{index:02d}" for index in range(1, 53)]
ROLE_RANK.update({role: index + 7 for index, role in enumerate(USER_RANKS)})
ROLE_RANK["creator"] = len(USER_RANKS) + 7
SYSTEM_ONLY_ROLES = {"system instrucsens"}
ROLE_RANK["system instrucsens"] = ROLE_RANK["creator"] + 1
ROLE_RANK.update({"HEADADMIN": 4, "SYSTEM": ROLE_RANK["system instrucsens"], "CO-OWNER": 5, "OWNER": 6, "Creater": ROLE_RANK["creator"]})
ROLE_ALIASES = {"HEADADMIN": "headadmin", "SYSTEM": "system instrucsens", "CO-OWNER": "co-owner", "OWNER": "owner", "Creater": "creator"}
SPECIAL_USER_ROLE_NAMES = (
    "Dawn Initiate", "Copper Scout", "Ember Runner", "Mist Warden", "Iron Seeker",
    "Quartz Guard", "Storm Herald", "Rune Keeper", "Frost Ranger", "Sky Smith",
    "Ash Captain", "Moon Sentry", "Star Forger", "Tide Walker", "Flame Caller",
    "Stone Binder", "Cloud Strider", "Void Watcher", "Sun Marshal", "Crystal Sage",
    "Night Pilot", "Thunder Knight", "River Oracle", "Wild Cartographer", "Glass Sentinel",
    "Solar Vanguard", "Lunar Envoy", "Obsidian Adept", "Aurora Knight", "Cinder Baron",
    "Tempest Lord", "Astral Commander", "Prism Magister", "Eclipse Warden", "Titan Architect",
    "Nebula Ranger", "Comet Chancellor", "Gravity Master", "Mirage Sovereign", "Chrono Keeper",
    "Radiant Regent", "Shadow Admiral", "Starlight Architect", "Infinite Pathfinder", "Celestial Judge",
    "Quantum Herald", "Eternal Guardian", "Dimension Weaver", "Cosmic Strategist", "Reality Shaper",
    "Prime Ascendant", "World Architect", "Grand Luminary", "Crown of Horizons", "Master of Realms",
    "Legendary Paragon", "Mythic Overlord", "Transcendent Lord", "Supreme Creator", "Creater",
)
SPECIAL_ROLE_NAMES = dict(zip(
    ["user", "mod", "op", "superop", "headadmin", "co-owner", "owner", *USER_RANKS, "creator"],
    SPECIAL_USER_ROLE_NAMES,
))
SPECIAL_ROLE_NAMES["system instrucsens"] = "System Instrucsens"
ROLE_FEATURES = {
    role: [f"{role} capability {index}" for index in range((rank + 1) * 100)]
    for role, rank in ROLE_RANK.items() if rank >= 0 and role not in ROLE_ALIASES
}
COMMANDS = (
    "tempban", "ban", "permban", "kill", "kick", "logs", "creative", "op", "deop", "superop",
    "desuperop", "delete", "give", "command_block", "scan", "report", "inspect", "repair", "heal",
    "teleport", "spawn", "home", "sethome", "time", "weather", "difficulty", "gamemode", "effect",
    "clear", "summon", "announce", "mute", "unmute", "warn", "jail", "unjail", "freeze", "unfreeze",
    "spectate", "vanish", "visible", "whitelist", "pardon", "backup", "restore", "reload", "status", "profile",
    "rank", "capabilities",
)
COMMAND_REQUIRED_ROLE = {command: "user" for command in COMMANDS}
COMMAND_REQUIRED_ROLE.update({
    command: "mod" for command in COMMANDS[16:]
})
COMMAND_REQUIRED_ROLE.update({
    "tempban": "op", "creative": "op", "kill": "op", "kick": "op", "logs": "op",
    "ban": "superop", "permban": "superop", "op": "superop", "deop": "superop",
    "superop": "owner", "desuperop": "owner", "delete": "owner", "give": "owner",
    "command_block": "owner",
})
SYSTEM_PERMISSION_DEFAULTS = {command: True for command in COMMANDS}
DEFAULT_SYSTEM_RULES = (
    "Severity Craft game rules:\n"
    "- Values 4-9 are errors.\n"
    "- USER < OP < SUPEROP < OWNER.\n"
    "- Only the owner may edit permissions.\n"
    "- Bans are checked when an account logs in."
)

# endregion

RANDOM_THINGS = [
    "apple", "bread", "carrot", "potato", "beetroot", "melon", "cookie", "cake", "coal", "iron_ingot",
    "gold_ingot", "diamond", "emerald", "redstone", "lapis_lazuli", "quartz", "amethyst", "copper_ingot",
    "stick", "torch", "lantern", "map", "compass", "clock", "bow", "arrow", "fishing_rod", "shield",
    "wooden_sword", "stone_sword", "iron_sword", "golden_sword", "diamond_sword", "wooden_pickaxe", "iron_pickaxe",
    "diamond_pickaxe", "wooden_axe", "iron_axe", "diamond_axe", "shears", "flint_and_steel", "bucket", "water_bucket",
    "lava_bucket", "leather", "string", "feather", "gunpowder", "bone", "ink_sac", "slimeball", "ender_pearl",
    "blaze_rod", "ghast_tear", "spider_eye", "rotten_flesh", "golden_apple", "book", "paper", "name_tag", "saddle",
    "lead", "bell", "note_block", "jukebox", "crafting_table", "furnace", "chest", "barrel", "hopper", "dropper",
    "dispenser", "rail", "minecart", "boat", "ladder", "door", "trapdoor", "glass", "brick", "stone", "cobblestone",
    "dirt", "grass_block", "sand", "gravel", "clay", "obsidian", "ice", "snowball", "flower", "sapling", "wheat",
    "pumpkin", "hay_bale", "bookshelf", "scaffolding", "firework", "experience_bottle", "dragon_breath", "beacon",
]

COMMAND_BLOCK_COMMANDS = (
    "say", "tell", "title", "give", "clear", "kill", "tp", "teleport", "summon", "setblock", "fill", "clone", "locate",
    "time", "weather", "difficulty", "gamemode", "gamerule", "effect", "enchant", "experience", "playsound", "particle",
    "schedule", "scoreboard", "tag", "team", "spreadplayers", "worldborder", "seed", "list", "me", "help", "whitelist",
    "kick", "ban", "pardon", "op", "deop", "stop",
)

# endregion


def is_error(number_value: int | None) -> bool:
    """Return whether a value represents an error that should be reported."""
    return number_value is not None and number_value >= 4


def role_display_name(role: str) -> str:
    """Return the special title shown to players for an internal role ID."""
    return SPECIAL_ROLE_NAMES.get(role, role.replace("-", " ").title())


# region Accounts and login

class AccountStore:
    """Loads and saves accounts, worlds, permissions, bans, and audit logs."""

    # region Account records and storage
    def __init__(self, path: Path) -> None:
        self.path = path
        self.logs: list[str] = []
        self.system_permissions: dict[str, bool] = dict(SYSTEM_PERMISSION_DEFAULTS)
        self.system_rules = DEFAULT_SYSTEM_RULES
        self.accounts: dict[str, dict[str, object]] = self.load()
        self.ensure_owner()
        self.ensure_system_accounts()

    def load(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if isinstance(data, dict) and isinstance(data.get("logs"), list):
            self.logs = [str(item) for item in data["logs"]]
        if isinstance(data, dict) and isinstance(data.get("system_permissions"), dict):
            for command, enabled in data["system_permissions"].items():
                if command in SYSTEM_PERMISSION_DEFAULTS:
                    self.system_permissions[command] = bool(enabled)
        if isinstance(data, dict) and isinstance(data.get("system_rules"), str):
            self.system_rules = data["system_rules"]
        accounts = data.get("accounts", {}) if isinstance(data, dict) else {}
        return accounts if isinstance(accounts, dict) else {}

    def save(self) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "accounts": self.accounts,
                    "logs": self.logs[-500:],
                    "system_permissions": self.system_permissions,
                    "system_rules": self.system_rules,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def record(self, message: str) -> None:
        self.logs.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}")
        self.save()

    # endregion

    # region Account passwords and authentication

    def set_password(self, username: str, password: str) -> None:
        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
        self.accounts[username]["salt"] = salt.hex()
        self.accounts[username]["password_hash"] = password_hash.hex()

    def ensure_owner(self) -> None:
        if "Jaxon" not in self.accounts:
            self.accounts["Jaxon"] = {"worlds": {}, "role": "Creater"}
            self.set_password("Jaxon", "1990")
            self.save()
        else:
            self.accounts["Jaxon"]["role"] = "Creater"
            if not self.verify("Jaxon", "1990"):
                self.set_password("Jaxon", "1990")
            self.save()

    def ensure_system_accounts(self) -> None:
        """Ensure the internal IT Services account exists without exposing its secret."""
        username = "IT Services"
        if username not in self.accounts:
            self.accounts[username] = {"worlds": {}, "role": "system instrucsens", "permissions": {}}
            self.set_password(username, secrets.token_urlsafe(24))
            self.save()
        elif self.accounts[username].get("role") != "system instrucsens":
            self.accounts[username]["role"] = "system instrucsens"
            self.save()

    def create_account(self, username: str, password: str, role: str = DEFAULT_PLAYER_ROLE, system_account: bool = False) -> bool:
        if username in self.accounts or role not in ROLE_RANK:
            return False
        if role in SYSTEM_ONLY_ROLES and not system_account:
            return False
        if system_account and role not in SYSTEM_ONLY_ROLES:
            return False
        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
        self.accounts[username] = {
            "salt": salt.hex(),
            "password_hash": password_hash.hex(),
            "worlds": {},
            "role": role,
            "permissions": {},
        }
        self.save()
        return True

    def create_system_account(self, username: str, password: str, role: str) -> bool:
        """Create a non-player account using one of the 24 system-only roles."""
        return self.create_account(username, password, role, system_account=True)

    def verify(self, username: str, password: str) -> bool:
        account = self.accounts.get(username)
        if not account:
            return False
        try:
            salt = bytes.fromhex(str(account["salt"]))
            expected_hash = bytes.fromhex(str(account["password_hash"]))
        except (KeyError, ValueError):
            return False
        actual_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
        return secrets.compare_digest(actual_hash, expected_hash)

    # endregion

    # region Players, roles, and permissions

    def worlds_for(self, username: str) -> dict[str, dict[str, object]]:
        account = self.accounts[username]
        worlds = account.setdefault("worlds", {})
        return worlds if isinstance(worlds, dict) else {}

    def role_for(self, username: str) -> str:
        role = self.accounts.get(username, {}).get("role", "user")
        role_name = str(role)
        return ROLE_ALIASES.get(role_name, role_name) if role_name in ROLE_RANK else "user"

    def capability_count_for(self, username: str) -> int:
        role = self.role_for(username)
        return len(ROLE_FEATURES.get(role, []))

    def permissions_for(self, username: str) -> dict[str, bool]:
        account = self.accounts[username]
        permissions = account.setdefault("permissions", {})
        return permissions if isinstance(permissions, dict) else {}

    def profile_for(self, username: str) -> dict[str, object]:
        """Return one player's account, role, and permission data together."""
        account = self.accounts[username]
        return {
            "username": username,
            "role": self.role_for(username),
            "permissions": self.permissions_for(username),
            "worlds": self.worlds_for(username),
        }

    def effective_permissions(self, username: str) -> set[str]:
        """Return commands inherited by the player's role plus explicit allows."""
        role = self.role_for(username)
        allowed = {
            command for command in COMMANDS
            if role != "banned"
            and (role in {"owner", "system instrucsens"} or self.system_permissions.get(command, True))
            and (
                command not in COMMAND_REQUIRED_ROLE
                or ROLE_RANK[role] >= ROLE_RANK[COMMAND_REQUIRED_ROLE[command]]
            )
        }
        overrides = self.permissions_for(username)
        allowed.update(
            command for command, enabled in overrides.items()
            if enabled
            and command in COMMANDS
            and role != "banned"
            and (role in {"owner", "system instrucsens"} or self.system_permissions.get(command, True))
        )
        allowed.difference_update(command for command, enabled in overrides.items() if not enabled)
        return allowed

    # endregion

    # region Account bans and deletion

    def is_banned(self, username: str) -> bool:
        account = self.accounts.get(username, {})
        banned_until = account.get("banned_until")
        if banned_until == "permanent":
            return True
        if isinstance(banned_until, (int, float)):
            if banned_until > time.time():
                return True
            account.pop("banned_until", None)
            self.save()
        return False

    def set_role(self, username: str, role: str) -> bool:
        if username not in self.accounts or role not in ROLE_RANK:
            return False
        self.accounts[username]["role"] = role
        self.save()
        return True

    def ban(self, username: str, days: int | None) -> bool:
        if username not in self.accounts:
            return False
        self.accounts[username]["banned_until"] = "permanent" if days is None else time.time() + days * 86400
        self.save()
        return True

    def delete_account(self, username: str) -> bool:
        if username == "Jaxon" or username not in self.accounts:
            return False
        del self.accounts[username]
        self.save()
        return True

    # endregion


class AccountDialog:
    """Provides the login and account-creation window."""

    # region Login form and account creation
    def __init__(self, parent: tk.Tk, store: AccountStore) -> None:
        self.store = store
        self.username: str | None = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Severity Craft Login")
        self.dialog.geometry("360x260")
        self.dialog.resizable(False, False)
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)

        frame = tk.Frame(self.dialog, background="#87ceeb", padx=24, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="SEVERITY CRAFT", font=("Segoe UI", 18, "bold"), background="#87ceeb", foreground="#17324d").pack()
        tk.Label(frame, text="Log in or create an account", background="#87ceeb", foreground="#17324d").pack(pady=(4, 14))

        self.username_entry = ttk.Entry(frame, width=30)
        self.username_entry.insert(0, "Username")
        self.username_entry.pack(pady=3)
        self.password_entry = ttk.Entry(frame, width=30, show="*")
        self.password_entry.pack(pady=3)
        self.status = tk.StringVar(value="Password must be at least 6 characters.")
        tk.Label(frame, textvariable=self.status, background="#87ceeb", foreground="#17324d").pack(pady=5)

        buttons = tk.Frame(frame, background="#87ceeb")
        buttons.pack()
        ttk.Button(buttons, text="Log in", command=self.login).pack(side="left", padx=4)
        ttk.Button(buttons, text="Create account", command=self.create_account).pack(side="left", padx=4)
        self.dialog.grab_set()

    def credentials(self) -> tuple[str, str]:
        return self.username_entry.get().strip(), self.password_entry.get()

    def valid_credentials(self, username: str, password: str) -> bool:
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,20}", username):
            self.status.set("Username: 3-20 letters, numbers, _ or -.")
            return False
        if len(password) < 6:
            self.status.set("Password must be at least 6 characters.")
            return False
        return True

    def login(self) -> None:
        username, password = self.credentials()
        if self.store.is_banned(username):
            self.status.set("This account is banned.")
        elif self.store.verify(username, password):
            self.username = username
            self.store.record(f"LOGIN {username}")
            self.dialog.destroy()
        else:
            self.status.set("Login failed. Check the username and password.")

    def create_account(self) -> None:
        username, password = self.credentials()
        if not self.valid_credentials(username, password):
            return
        if self.store.create_account(username, password):
            self.username = username
            self.dialog.destroy()
        else:
            self.status.set("That username already exists.")

    def cancel(self) -> None:
        self.dialog.destroy()

    # endregion


# endregion


# region Main game

class SeverityGame:
    """Owns the game window, player state, world, inventory, and game rules."""
    def __init__(self, window: tk.Tk, username: str, account_store: AccountStore) -> None:
        self.window = window
        self.username = username
        self.account_store = account_store
        self.role = account_store.role_for(username)
        self.window.title("Severity Scanner")
        self.window.geometry("720x600")
        self.window.minsize(720, 600)
        self.window.resizable(True, True)
        self.fullscreen = False
        self.window.bind("<F11>", lambda _event: self.toggle_fullscreen())
        self.window.bind("<Escape>", lambda _event: self.leave_fullscreen())
        self.level = 1
        self.score = 0
        self.current_value: int | None = None
        self.world_columns = 8
        self.world_rows = 4
        self.block_size = 78
        self.blocks: list[int | None] = []
        self.mined_blocks: set[int] = set()
        self.command_blocks: set[int] = set()
        self.command_block_commands: dict[str, str] = {}
        self.block_materials: dict[str, str] = {}
        self.inventory: dict[str, int] = {"dirt": 8, "stone": 8, "cobblestone": 4}
        self.selected_item = "dirt"
        self.player_x = PLAYER_START_X
        self.player_y = PLAYER_START_Y
        self.player_angle = PLAYER_START_ANGLE
        self.move_step = 0.28
        self.turn_step = math.radians(10)
        self.selected_block: int | None = None
        self.world_name = "New World"
        self.creative_mode = False
        self.command_block_mode = False
        self.mini_game_window: tk.Toplevel | None = None
        self.mini_values: list[int | None] = []
        self.mini_score = 0
        self.level_text = tk.StringVar()
        self.value_text = tk.StringVar()
        self.inventory_text = tk.StringVar()
        self.world_text = tk.StringVar(value=self.world_name)
        self.report_text = tk.StringVar(value="Choose whether the current value is an error.")

        self.build_ui()
        self.new_round()

    # region Player state and controls

    # region User interface and window controls

    def build_ui(self) -> None:
        self.window.configure(background="#87ceeb")
        main = tk.Frame(self.window, background="#87ceeb", padx=18, pady=14)
        main.pack(fill="both", expand=True)

        header = tk.Frame(main, background="#87ceeb")
        header.pack(fill="x")
        tk.Label(
            header,
            text="SEVERITY CRAFT",
            font=("Segoe UI", 20, "bold"),
            background="#87ceeb",
            foreground="#17324d",
        ).pack(side="left")
        tk.Label(
            header,
            text=f"PLAYER: {self.username}",
            font=("Segoe UI", 11, "bold"),
            background="#87ceeb",
            foreground="#17324d",
        ).pack(side="right", padx=(0, 14))
        tk.Label(
            header,
            textvariable=self.level_text,
            font=("Segoe UI", 11, "bold"),
            background="#87ceeb",
            foreground="#17324d",
        ).pack(side="right")
        tk.Label(
            header,
            text=f"RANK {ROLE_RANK[self.role]}: {role_display_name(self.role)} | {self.account_store.capability_count_for(self.username)} FEATURES",
            font=("Segoe UI", 10, "bold"),
            background="#87ceeb",
            foreground="#17324d",
        ).pack(side="right", padx=(0, 14))
        tk.Button(header, text="Log out", command=self.logout).pack(side="right", padx=(0, 6))
        tk.Button(header, text="Fullscreen (F11)", command=self.toggle_fullscreen).pack(side="right", padx=(0, 12))

        tk.Label(
            main,
            textvariable=self.world_text,
            font=("Segoe UI", 13, "bold"),
            background="#87ceeb",
            foreground="#17324d",
        ).pack(pady=(4, 2))
        tk.Label(main, text="WASD: walk   Left/Right: turn   Space or click: mine the block ahead. Severity values are hidden.", background="#87ceeb", foreground="#17324d").pack(pady=(0, 8))

        self.world = tk.Canvas(
            main,
            width=self.world_columns * self.block_size,
            height=self.world_rows * self.block_size,
            background="#9cdbf5",
            highlightthickness=4,
            highlightbackground="#315d72",
        )
        self.world.pack(fill="both", expand=True)
        self.world.bind("<Button-1>", self.mine_block)
        self.world.bind("<Configure>", self.resize_world)
        self.world.bind("<KeyPress>", self.handle_key)
        self.world.focus_set()

        hud = tk.Frame(main, background="#17324d", padx=12, pady=8)
        hud.pack(fill="x", pady=(10, 8))
        tk.Label(hud, text="MINED BLOCK", background="#17324d", foreground="#b9e7ff").pack(side="left")
        tk.Label(hud, textvariable=self.value_text, background="#17324d", foreground="white", font=("Segoe UI", 13, "bold")).pack(side="left", padx=12)
        tk.Label(hud, textvariable=self.inventory_text, background="#17324d", foreground="#ffe082", font=("Segoe UI", 10, "bold")).pack(side="left", padx=12)

        self.status = tk.Label(
            main,
            textvariable=self.report_text,
            anchor="w",
            justify="left",
            wraplength=650,
            bg="#d9f1ff",
            foreground="#17324d",
            padx=12,
            pady=8,
        )
        self.status.pack(fill="x", pady=(0, 10))

        buttons = tk.Frame(main, background="#87ceeb")
        buttons.pack()
        tk.Button(buttons, text="Report error", command=lambda: self.submit(True), width=14).pack(side="left", padx=4)
        tk.Button(buttons, text="Report safe", command=lambda: self.submit(False), width=14).pack(side="left", padx=4)
        tk.Button(buttons, text="New world", command=self.new_round, width=14).pack(side="left", padx=4)
        tk.Button(buttons, text="Manage worlds", command=self.open_world_manager, width=16).pack(side="left", padx=4)
        tk.Button(buttons, text="Error amount mine", command=self.open_error_amount_game, width=16).pack(side="left", padx=4)
        tk.Button(buttons, text="INFO", command=self.open_permissions_window, width=14).pack(side="left", padx=4)
        if self.is_system_role():
            tk.Button(buttons, text="DEV INFO", command=self.open_dev_info_window, width=14).pack(side="left", padx=4)
        tk.Button(buttons, text="Command blocks", command=self.open_command_block_editor, width=16).pack(side="left", padx=4)
        tk.Button(buttons, text="Inventory (E)", command=self.open_inventory, width=16).pack(side="left", padx=4)
        if ROLE_RANK[self.role] >= ROLE_RANK["op"]:
            panel_name = "Admin panel" if ROLE_RANK[self.role] >= ROLE_RANK["superop"] else "OP menu"
            tk.Button(buttons, text=panel_name, command=self.open_admin_panel, width=14).pack(side="left", padx=4)
        if ROLE_RANK[self.role] >= ROLE_RANK["owner"]:
            tk.Button(buttons, text="Edit permissions", command=self.open_permission_editor, width=16).pack(side="left", padx=4)

        tk.Label(main, text="Mine carefully and report the real error amount.", background="#87ceeb", foreground="#17324d").pack(pady=(8, 0))

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.window.attributes("-fullscreen", self.fullscreen)

    def leave_fullscreen(self) -> None:
        if self.fullscreen:
            self.fullscreen = False
            self.window.attributes("-fullscreen", False)

    def resize_world(self, event: tk.Event) -> None:
        available_width = max(320, int(event.width))
        available_height = max(180, int(event.height))
        new_block_size = max(40, min(130, min(available_width // self.world_columns, available_height // self.world_rows)))
        if new_block_size != self.block_size:
            self.block_size = new_block_size
            self.draw_world()

    def new_round(self) -> None:
        self.blocks = [random.choice([None, *range(10)]) for _ in range(self.world_columns * self.world_rows)]
        self.mined_blocks.clear()
        self.command_blocks.clear()
        self.command_block_commands.clear()
        self.block_materials.clear()
        self.inventory = {"dirt": 8, "stone": 8, "cobblestone": 4}
        self.selected_item = "dirt"
        self.selected_block = None
        self.current_value = None
        self.value_text.set("Severity checked internally")
        self.report_text.set("Mine a block to reveal its severity.")
        self.status.configure(background="#d9f1ff", foreground="#17324d")
        self.refresh_inventory_text()
        self.draw_world()

    # endregion

    # region Player movement and camera

    def handle_key(self, event: tk.Event) -> str:
        key = str(event.keysym).lower()
        if key in {"left", "a"}:
            self.player_angle -= self.turn_step
        elif key in {"right", "d"}:
            self.player_angle += self.turn_step
        elif key in {"up", "w", "down", "s"}:
            direction = 1 if key in {"up", "w"} else -1
            next_x = self.player_x + math.cos(self.player_angle) * self.move_step * direction
            next_y = self.player_y + math.sin(self.player_angle) * self.move_step * direction
            if self.walkable(next_x, next_y):
                self.player_x, self.player_y = next_x, next_y
        elif key == "space":
            self.mine_facing_block()
        elif key == "e":
            self.open_inventory()
        elif key == "p" or key == "return":
            self.place_facing_block()
        elif key in {str(number) for number in range(1, 10)}:
            self.select_inventory_slot(int(key) - 1)
        else:
            return "break"
        self.draw_world()
        return "break"

    # region Inventory and items

    def refresh_inventory_text(self) -> None:
        visible_items = [f"[{index + 1}] {item}:{amount}" for index, (item, amount) in enumerate(self.inventory.items()) if amount > 0][:9]
        selected_amount = self.inventory.get(self.selected_item, 0)
        self.inventory_text.set(f"HOTBAR {' | '.join(visible_items)}   SELECTED: {self.selected_item} x{selected_amount}")

    def select_inventory_slot(self, slot: int) -> None:
        items = [item for item, amount in self.inventory.items() if amount > 0]
        if slot < len(items):
            self.selected_item = items[slot]
            self.refresh_inventory_text()
            self.draw_world()

    def add_item(self, item: str, amount: int = 1) -> None:
        self.inventory[item] = self.inventory.get(item, 0) + amount
        self.refresh_inventory_text()

    def open_inventory(self) -> None:
        inventory_window = tk.Toplevel(self.window)
        inventory_window.title("Inventory")
        inventory_window.geometry("430x420")
        frame = ttk.Frame(inventory_window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="INVENTORY", font=("Segoe UI", 16, "bold")).pack()
        ttk.Label(frame, text="Select an item, then press P or Enter to place it in front of you.").pack(pady=6)
        item_list = tk.Listbox(frame, height=15, exportselection=False)
        item_list.pack(fill="both", expand=True, pady=8)
        for item, amount in sorted(self.inventory.items()):
            item_list.insert(tk.END, f"{item} x{amount}")

        def select_item(_event: tk.Event | None = None) -> None:
            selection = item_list.curselection()
            if selection:
                self.selected_item = sorted(self.inventory)[selection[0]]
                self.refresh_inventory_text()

        item_list.bind("<<ListboxSelect>>", select_item)
        ttk.Button(frame, text="Select", command=select_item).pack()

    def place_facing_block(self) -> None:
        if self.inventory.get(self.selected_item, 0) <= 0:
            self.report_text.set(f"You have no {self.selected_item} to place.")
            return
        target = None
        for distance_step in range(4, 16):
            distance = distance_step / 10
            x = self.player_x + math.cos(self.player_angle) * distance
            y = self.player_y + math.sin(self.player_angle) * distance
            if not (0 <= x < self.world_columns and 0 <= y < self.world_rows):
                break
            candidate = int(y) * self.world_columns + int(x)
            if candidate != int(self.player_y) * self.world_columns + int(self.player_x):
                target = candidate
                if candidate in self.mined_blocks:
                    break
        if target is None or target not in self.mined_blocks:
            self.report_text.set("Aim at an empty space to place a block.")
            return
        self.mined_blocks.remove(target)
        self.blocks[target] = random.choice([None, *range(10)])
        self.block_materials[str(target)] = self.selected_item
        self.inventory[self.selected_item] -= 1
        self.selected_block = target
        self.report_text.set(f"Placed {self.selected_item}.")
        self.refresh_inventory_text()
        self.draw_world()

    # endregion

    def walkable(self, x: float, y: float) -> bool:
        return 0.2 < x < self.world_columns - 0.2 and 0.2 < y < self.world_rows - 0.2

    # endregion

    # region World save and load

    # region World data and save/load

    def world_data(self) -> dict[str, object]:
        return {
            "blocks": self.blocks,
            "mined_blocks": sorted(self.mined_blocks),
            "command_blocks": sorted(self.command_blocks),
            "command_block_commands": self.command_block_commands,
            "block_materials": self.block_materials,
            "inventory": self.inventory,
            "selected_item": self.selected_item,
            "score": self.score,
            "level": self.level,
        }

    def save_world(self) -> None:
        name = self.world_name.strip()
        if not name:
            self.report_text.set("Give this world a name before saving it.")
            return
        self.account_store.worlds_for(self.username)[name] = self.world_data()
        self.account_store.save()
        self.report_text.set(f"World '{name}' saved for {self.username}.")

    def open_world_manager(self) -> None:
        if hasattr(self, "world_manager") and self.world_manager.winfo_exists():
            self.world_manager.lift()
            self.refresh_world_list()
            return

        self.world_manager = tk.Toplevel(self.window)
        self.world_manager.title(f"Worlds for {self.username}")
        self.world_manager.geometry("400x360")
        self.world_manager.resizable(False, False)
        frame = ttk.Frame(self.world_manager, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="SAVED WORLDS", font=("Segoe UI", 14, "bold")).pack()
        self.world_list = tk.Listbox(frame, height=9, exportselection=False)
        self.world_list.pack(fill="both", expand=True, pady=10)

        name_row = ttk.Frame(frame)
        name_row.pack(fill="x", pady=(0, 8))
        ttk.Label(name_row, text="New name:").pack(side="left")
        self.new_world_name = ttk.Entry(name_row)
        self.new_world_name.pack(side="left", fill="x", expand=True, padx=(8, 0))

        actions = ttk.Frame(frame)
        actions.pack()
        ttk.Button(actions, text="Save current", command=self.save_world).pack(side="left", padx=3)
        ttk.Button(actions, text="Create new", command=self.create_world).pack(side="left", padx=3)
        ttk.Button(actions, text="Load selected", command=self.load_selected_world).pack(side="left", padx=3)
        ttk.Button(actions, text="Delete selected", command=self.delete_selected_world).pack(side="left", padx=3)
        self.refresh_world_list()

    def refresh_world_list(self) -> None:
        if not hasattr(self, "world_list") or not self.world_list.winfo_exists():
            return
        self.world_list.delete(0, tk.END)
        for name in sorted(self.account_store.worlds_for(self.username)):
            self.world_list.insert(tk.END, name)

    def create_world(self) -> None:
        name = self.new_world_name.get().strip()
        if not name:
            messagebox.showinfo("World name", "Enter a name for the new world.", parent=self.world_manager)
            return
        if name in self.account_store.worlds_for(self.username):
            messagebox.showinfo("World name", "That world already exists.", parent=self.world_manager)
            return
        self.world_name = name
        self.world_text.set(name)
        self.new_round()
        self.save_world()
        self.new_world_name.delete(0, tk.END)
        self.refresh_world_list()

    def load_selected_world(self) -> None:
        selection = self.world_list.curselection()
        if not selection:
            return
        name = self.world_list.get(selection[0])
        saved = self.account_store.worlds_for(self.username)[name]
        if not isinstance(saved, dict):
            return
        blocks = saved.get("blocks", [])
        mined_blocks = saved.get("mined_blocks", [])
        command_blocks = saved.get("command_blocks", [])
        command_block_commands = saved.get("command_block_commands", {})
        block_materials = saved.get("block_materials", {})
        if not isinstance(blocks, list) or len(blocks) != self.world_columns * self.world_rows:
            messagebox.showerror("Load failed", "This saved world is invalid.", parent=self.world_manager)
            return
        self.world_name = name
        self.world_text.set(name)
        self.blocks = [value if isinstance(value, int) or value is None else None for value in blocks]
        self.mined_blocks = {int(index) for index in mined_blocks if isinstance(index, int) and 0 <= index < len(self.blocks)}
        self.command_blocks = {int(index) for index in command_blocks if isinstance(index, int) and 0 <= index < len(self.blocks)}
        self.command_block_commands = {
            str(index): str(command) for index, command in command_block_commands.items()
            if str(index).isdigit() and int(index) in self.command_blocks
        } if isinstance(command_block_commands, dict) else {}
        self.block_materials = {
            str(index): str(material) for index, material in block_materials.items()
            if str(index).isdigit() and 0 <= int(index) < len(self.blocks)
        } if isinstance(block_materials, dict) else {}
        saved_inventory = saved.get("inventory", {})
        self.inventory = {
            str(item): int(amount) for item, amount in saved_inventory.items()
            if isinstance(item, str) and isinstance(amount, int) and amount > 0
        } if isinstance(saved_inventory, dict) else {"dirt": 8, "stone": 8}
        if not self.inventory:
            self.inventory = {"dirt": 8, "stone": 8}
        self.selected_item = str(saved.get("selected_item", next(iter(self.inventory))))
        self.selected_block = None
        self.current_value = None
        self.score = int(saved.get("score", 0))
        self.level = int(saved.get("level", 1))
        self.level_text.set(f"LEVEL {self.level}   SCORE {self.score}")
        self.value_text.set("Severity checked internally")
        self.report_text.set(f"World '{name}' loaded. Mine a block.")
        self.status.configure(background="#d9f1ff", foreground="#17324d")
        self.refresh_inventory_text()
        self.draw_world()

    def delete_selected_world(self) -> None:
        selection = self.world_list.curselection()
        if not selection:
            return
        name = self.world_list.get(selection[0])
        if not messagebox.askyesno("Delete world", f"Delete '{name}' permanently?", parent=self.world_manager):
            return
        del self.account_store.worlds_for(self.username)[name]
        self.account_store.save()
        if name == self.world_name:
            self.world_name = "New World"
            self.world_text.set(self.world_name)
            self.new_round()
        self.refresh_world_list()

    # endregion
    # endregion

    # region Permissions and administration

    # region Role rules

    def command_allowed(self, command: str) -> bool:
        return command in self.account_store.effective_permissions(self.username)

    def is_system_role(self) -> bool:
        return self.role == "system instrucsens"

    # endregion

    # region Role administration

    def open_admin_panel(self) -> None:
        if ROLE_RANK[self.role] < ROLE_RANK["op"]:
            return
        panel = tk.Toplevel(self.window)
        panel.title(f"{role_display_name(self.role)} MENU - {self.username}")
        panel.geometry("520x460")
        panel.resizable(False, False)
        frame = ttk.Frame(panel, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"{role_display_name(self.role)} COMMAND PANEL", font=("Segoe UI", 15, "bold")).pack()
        ttk.Label(frame, text=self.command_help()).pack(pady=(6, 12))

        target_row = ttk.Frame(frame)
        target_row.pack(fill="x", pady=3)
        ttk.Label(target_row, text="Target:", width=10).pack(side="left")
        self.command_target = ttk.Entry(target_row)
        self.command_target.pack(side="left", fill="x", expand=True)

        days_row = ttk.Frame(frame)
        days_row.pack(fill="x", pady=3)
        ttk.Label(days_row, text="Days:", width=10).pack(side="left")
        self.command_days = ttk.Entry(days_row)
        self.command_days.insert(0, "1")
        self.command_days.pack(side="left", fill="x", expand=True)

        command_row = ttk.Frame(frame)
        command_row.pack(fill="x", pady=3)
        ttk.Label(command_row, text="Command:", width=10).pack(side="left")
        self.command_entry = ttk.Entry(command_row)
        self.command_entry.pack(side="left", fill="x", expand=True)
        self.command_entry.bind("<KeyRelease>", self.update_command_suggestions)
        self.command_entry.bind("<Tab>", self.complete_command)
        ttk.Button(command_row, text="Run", command=self.run_admin_command).pack(side="left", padx=(8, 0))

        self.admin_status = tk.StringVar(value="Use a slash command, for example /creative or /logs.")
        ttk.Label(frame, textvariable=self.admin_status, wraplength=470).pack(pady=10)
        self.command_suggestions = tk.StringVar(value="Suggestions: " + ", ".join(f"/{command}" for command in COMMANDS))
        ttk.Label(frame, textvariable=self.command_suggestions, wraplength=470, justify="left").pack()
        self.log_box = tk.Listbox(frame, height=12)
        self.log_box.pack(fill="both", expand=True)
        self.refresh_admin_logs()

    def update_command_suggestions(self, _event: tk.Event | None = None) -> None:
        typed = self.command_entry.get().strip().lower().lstrip("/")
        matches = [command for command in COMMANDS if command.startswith(typed)] if typed else list(COMMANDS)
        if matches:
            self.command_suggestions.set("Suggestions: " + ", ".join(f"/{command}" for command in matches[:12]))
        else:
            self.command_suggestions.set("Suggestions: no matching commands")

    def complete_command(self, _event: tk.Event | None = None) -> str:
        typed = self.command_entry.get().strip()
        prefix = typed.lstrip("/").lower()
        matches = [command for command in COMMANDS if command.startswith(prefix)]
        if matches:
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, f"/{matches[0]} ")
            self.update_command_suggestions()
        return "break"

    # endregion

    # region Permission editor

    def open_permission_editor(self) -> None:
        if ROLE_RANK[self.role] < ROLE_RANK["owner"]:
            return
        editor = tk.Toplevel(self.window)
        editor.title("Owner Permission Editor")
        editor.geometry("760x680")
        editor.resizable(False, False)
        frame = ttk.Frame(editor, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="OWNER PERMISSION EDITOR", font=("Segoe UI", 15, "bold")).pack()
        ttk.Label(frame, text="Higher roles inherit lower-role commands. An unchecked command is an explicit negative permission.").pack(pady=(3, 10))

        account_row = ttk.Frame(frame)
        account_row.pack(fill="x")
        ttk.Label(account_row, text="Account:").pack(side="left")
        self.permission_account = ttk.Combobox(account_row, values=sorted(self.account_store.accounts), state="readonly", width=24)
        self.permission_account.pack(side="left", padx=8)
        self.permission_account.bind("<<ComboboxSelected>>", lambda _event: self.load_account_permissions())
        ttk.Button(account_row, text="Load account", command=self.load_account_permissions).pack(side="left")
        self.permission_role_text = tk.StringVar(value="Select an account")
        ttk.Label(frame, textvariable=self.permission_role_text).pack(anchor="w", pady=(5, 4))

        account_box = ttk.LabelFrame(frame, text="Individual account command permissions")
        account_box.pack(fill="x", pady=5)
        self.account_permission_vars: dict[str, tk.BooleanVar] = {}
        for index, command in enumerate(COMMANDS):
            variable = tk.BooleanVar(value=False)
            self.account_permission_vars[command] = variable
            tk.Checkbutton(account_box, text=f"/{command}", variable=variable, background="#f0f0f0").grid(row=index // 4, column=index % 4, sticky="w", padx=8, pady=2)
        ttk.Button(account_box, text="Save account permissions", command=self.save_account_permissions).grid(row=4, column=0, columnspan=4, pady=6)

        system_box = ttk.LabelFrame(frame, text="System-level command modules")
        system_box.pack(fill="x", pady=5)
        self.system_permission_vars: dict[str, tk.BooleanVar] = {}
        for index, command in enumerate(COMMANDS):
            variable = tk.BooleanVar(value=self.account_store.system_permissions.get(command, True))
            self.system_permission_vars[command] = variable
            tk.Checkbutton(system_box, text=f"Enable /{command} globally", variable=variable, background="#f0f0f0").grid(row=index // 3, column=index % 3, sticky="w", padx=8, pady=2)
        ttk.Button(system_box, text="Save system permissions", command=self.save_system_permissions).grid(row=5, column=0, columnspan=3, pady=6)

        ttk.Label(frame, text="Editable game system rules").pack(anchor="w", pady=(6, 2))
        self.system_rules_text = tk.Text(frame, height=6, width=88, wrap="word")
        self.system_rules_text.pack(fill="x")
        self.system_rules_text.insert("1.0", self.account_store.system_rules)
        ttk.Button(frame, text="Save system rules", command=self.save_system_rules).pack(pady=6)
        self.permission_status = tk.StringVar(value="Owner-only settings.")
        ttk.Label(frame, textvariable=self.permission_status).pack()

    def load_account_permissions(self) -> None:
        username = self.permission_account.get()
        if username not in self.account_store.accounts:
            return
        permissions = self.account_store.permissions_for(username)
        role = self.account_store.role_for(username)
        self.permission_role_text.set(f"{username} role: {role_display_name(role)} | Unchecked means denied")
        for command, variable in self.account_permission_vars.items():
            variable.set(bool(permissions.get(command, False)))

    def save_account_permissions(self) -> None:
        username = self.permission_account.get()
        if username not in self.account_store.accounts or (username == "Jaxon" and not self.is_system_role()):
            self.permission_status.set("The owner account cannot be edited here.")
            return
        permissions = self.account_store.permissions_for(username)
        for command, variable in self.account_permission_vars.items():
            permissions[command] = variable.get()
        self.account_store.save()
        self.account_store.record(f"{self.username} edited permissions for {username}")
        self.permission_status.set(f"Saved individual permissions for {username}.")

    def save_system_permissions(self) -> None:
        for command, variable in self.system_permission_vars.items():
            self.account_store.system_permissions[command] = variable.get()
        self.account_store.save()
        self.account_store.record(f"{self.username} edited system-level command permissions")
        self.permission_status.set("Saved system-level command permissions.")

    def save_system_rules(self) -> None:
        self.account_store.system_rules = self.system_rules_text.get("1.0", "end-1c")
        self.account_store.save()
        self.account_store.record(f"{self.username} edited game system rules")
        self.permission_status.set("Saved editable game system rules.")

    # endregion

    # region Permission display

    def open_permissions_window(self) -> None:
        info_window = tk.Toplevel(self.window)
        info_window.title("Severity Craft INFO")
        info_window.geometry("820x680")
        info_window.resizable(False, False)
        frame = ttk.Frame(info_window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="SEVERITY CRAFT INFO", font=("Segoe UI", 15, "bold")).pack()
        ttk.Label(frame, text=f"Logged in as: {self.username} | Current role: {role_display_name(self.role)}").pack(pady=(4, 10))

        text = tk.Text(frame, width=82, height=28, wrap="word", state="normal")
        text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        scrollbar.pack(side="right", fill="y")
        text.configure(yscrollcommand=scrollbar.set)
        text.insert("1.0", self.permission_text())
        text.configure(state="disabled")

    def open_dev_info_window(self) -> None:
        if not self.is_system_role():
            return
        dev_window = tk.Toplevel(self.window)
        dev_window.title("System Instrucsens Developer Info")
        dev_window.geometry("900x720")
        dev_window.resizable(False, False)
        frame = ttk.Frame(dev_window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="SYSTEM INSTRUCSENS DEVELOPER INFO", font=("Segoe UI", 15, "bold")).pack()
        ttk.Label(frame, text="System-only diagnostic and configuration information. Secrets and source contents are excluded.").pack(pady=(4, 10))
        text = tk.Text(frame, width=105, height=38, wrap="word", state="normal")
        text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        scrollbar.pack(side="right", fill="y")
        text.configure(yscrollcommand=scrollbar.set)
        text.insert("1.0", self.dev_info_text())
        text.configure(state="disabled")

    def dev_info_text(self) -> str:
        safe_accounts = []
        for username in sorted(self.account_store.accounts):
            account = self.account_store.accounts[username]
            safe_accounts.append(
                f"- {username}: role={role_display_name(self.account_store.role_for(username))}; "
                f"fields={', '.join(sorted(key for key in account if key not in {'salt', 'password_hash'}))}"
            )
        return f"""SYSTEM INSTRUCSENS DEVELOPER INFO
=================================
Access: system instrucsens only
Source file: {Path(__file__).name}
Account store: {self.account_store.path.name}

SECURITY BOUNDARY
=================
Passwords, password hashes, salts, session secrets, and other credentials are never displayed.
The complete source code is not rendered in the game window. Use the local source file for code review.

ROLES
=====
{', '.join(f'{role}={rank}' for role, rank in ROLE_RANK.items())}

COMMANDS
========
{', '.join(f'/{command}' for command in COMMANDS)}

COMMAND REQUIREMENTS
====================
{chr(10).join(f'/{command}: {required}' for command, required in COMMAND_REQUIRED_ROLE.items())}

ACCOUNTS WITHOUT SECRETS
========================
{chr(10).join(safe_accounts) or '- none'}

SYSTEM RULES
============
{self.account_store.system_rules}

CURRENT GAME STATE
==================
Player: {self.username}
World: {self.world_name}
Position: {self.player_x:.2f}, {self.player_y:.2f}
Level: {self.level}
Score: {self.score}
Mined blocks: {len(self.mined_blocks)} / {len(self.blocks)}
Inventory: {self.inventory}
Selected item: {self.selected_item}
Creative mode: {self.creative_mode}
Command block mode: {self.command_block_mode}

AUDIT LOGS
==========
{chr(10).join(self.account_store.logs[-100:]) or '- no audit events'}
"""

    # endregion

    # region Permission editor and rule text

    def permission_text(self) -> str:
        account_lines = []
        for username in sorted(self.account_store.accounts):
            role = self.account_store.role_for(username)
            worlds = ", ".join(sorted(self.account_store.worlds_for(username))) or "none"
            commands = ", ".join(sorted(self.account_store.effective_permissions(username))) or "none"
            banned = "yes" if self.account_store.is_banned(username) else "no"
            account_lines.append(
                f"- {username}: role={role_display_name(role)}; rank={ROLE_RANK[role]}; "
                f"banned={banned}; worlds={worlds}; commands={commands}"
            )
        enabled_modules = ", ".join(
            f"/{command}" for command, enabled in self.account_store.system_permissions.items() if enabled
        ) or "none"
        audit_logs = "\n".join(self.account_store.logs[-100:]) or "- no audit events"
        return f"""GAME INFO
    =========
    No passwords, password hashes, salts, or password secrets are displayed here.
    Logged-in account: {self.username}
    Role: {role_display_name(self.role)}
    Rank: {ROLE_RANK[self.role]}
    Capabilities: {self.account_store.capability_count_for(self.username)}
    Current world: {self.world_name}
    Current level and score: {self.level}, {self.score}
    Inventory: {self.inventory}
    Selected item: {self.selected_item}
    Mined blocks: {len(self.mined_blocks)} / {len(self.blocks)}

    ACCOUNTS
    ========
    {chr(10).join(account_lines) or "- none"}

    ENABLED SYSTEM COMMAND MODULES
    ==============================
    {enabled_modules}

    GAME RULES
    =========
    Every account starts as USER. Permissions are enforced when commands run.
The role hierarchy is USER < OP < SUPEROP < OWNER.
The owner account is Jaxon. The owner cannot be banned or deleted.

    OWNER-EDITED SYSTEM RULES
    =========================
    {self.account_store.system_rules}

ROLE PERMISSIONS
===============
USER
- Mine blocks, report errors, play the error-amount mini-game.
- Create, save, load, and delete their own worlds.
- No moderation or server commands.

OP
- Everything a USER can do.
- /tempban <user> <days>: maximum 10 days.
- /kill <user>, /kick <user>, /creative, /logs.
- Cannot ban permanently, change roles, or delete accounts.

SUPEROP
- Everything an OP can do.
- /ban <user> and /permban <user>: permanent ban.
- /op <user> and /deop <user>.
- /tempban has the same 10-day maximum.
- Cannot promote a user to SUPEROP or delete accounts.

OWNER
- Everything a SUPEROP can do.
- /superop <user> and /desuperop <user>.
- /delete <user>, /give <user> <item>, /Command_Block.
- Command blocks are red and persist inside saved worlds.

COMMAND MODULES
===============
ACCOUNT: salted password hashes, login, roles, and ban checks.
WORLDS: per-account named world save/load/create/delete.
MODERATION: kick, kill, temporary bans, permanent bans, account deletion.
AUDIT LOGS: command and login events are stored locally and shown to staff.
GAMEPLAY: block mining, severity reporting, levels, scores, creative mode.
MINI-GAME: count the real errors in a five-value challenge.
COMMAND BLOCKS: owner-only placement mode; placed blocks render red.

AUDIT LOGS
==========
{audit_logs}

This INFO panel excludes all password data.
"""

    def command_help(self) -> str:
        if self.role == "system instrucsens":
            return "SYSTEM INSTRUCSENS: unrestricted access to all commands and system settings"
        if self.role == "op":
            return "OP: /tempban (10 days max) /kill /creative /logs /kick"
        if self.role == "superop":
            return "SUPEROP: /ban /logs /creative /op /deop /kick /kill /tempban /permban"
        return "OWNER: all superop commands + /delete /superop /desuperop /give /Command_Block"

    # region Command blocks

    def logout(self) -> None:
        self.account_store.record(f"LOGOUT {self.username}")
        self.window.destroy()

    def open_command_block_editor(self) -> None:
        editor = tk.Toplevel(self.window)
        editor.title("Command Block Console")
        editor.geometry("560x430")
        frame = ttk.Frame(editor, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="COMMAND BLOCK CONSOLE", font=("Segoe UI", 15, "bold")).pack()
        ttk.Label(frame, text="Place a red block in command-block mode, select it, then enter a Minecraft-style command.").pack(pady=6)
        command_entry = ttk.Entry(frame)
        command_entry.pack(fill="x", pady=6)
        command_entry.insert(0, "/say Hello from the command block")
        output = tk.StringVar(value="40 commands available: " + ", ".join(COMMAND_BLOCK_COMMANDS))
        ttk.Label(frame, textvariable=output, wraplength=520, justify="left").pack(fill="x", pady=8)
        ttk.Button(frame, text="Save to selected block", command=lambda: self.save_command_block(command_entry.get(), output)).pack(pady=4)
        ttk.Button(frame, text="Run selected block", command=lambda: self.run_selected_command_block(output)).pack(pady=4)

    def save_command_block(self, command: str, output: tk.StringVar) -> None:
        if self.selected_block is None or self.selected_block not in self.command_blocks:
            output.set("Select a red command block first.")
            return
        command = command.strip()
        name = command.lstrip("/").split(maxsplit=1)[0].lower() if command else ""
        if name not in COMMAND_BLOCK_COMMANDS:
            output.set("Unknown command. Use one of the 40 commands listed above.")
            return
        self.command_block_commands[str(self.selected_block)] = command
        self.account_store.record(f"{self.username} configured command block {self.selected_block}: {command}")
        output.set(f"Saved: {command}")
        self.draw_world()

    def run_selected_command_block(self, output: tk.StringVar) -> None:
        if self.selected_block is None or self.selected_block not in self.command_blocks:
            output.set("Select a red command block first.")
            return
        command = self.command_block_commands.get(str(self.selected_block))
        if not command:
            output.set("This command block has no command yet.")
            return
        parts = shlex.split(command.lstrip("/"))
        result = self.execute_command_block(parts[0].lower(), parts[1:])
        output.set(result)

    def execute_command_block(self, command: str, arguments: list[str]) -> str:
        text = " ".join(arguments)
        if command in {"say", "tell", "title", "me"}:
            message = text or "Command block activated."
            self.report_text.set(message)
            self.account_store.record(f"COMMAND_BLOCK /{command} {message}")
            return message
        if command == "give":
            item = arguments[1] if len(arguments) > 1 else random.choice(RANDOM_THINGS)
            return f"Command block gave {item}."
        if command == "summon":
            return f"Summoned {arguments[0] if arguments else 'pig'}."
        self.account_store.record(f"COMMAND_BLOCK /{command} {text}".rstrip())
        return f"Executed /{command} {text}".rstrip()

    # endregion

    # region Admin commands and audit logs

    def refresh_admin_logs(self) -> None:
        if not hasattr(self, "log_box") or not self.log_box.winfo_exists():
            return
        self.log_box.delete(0, tk.END)
        for log in self.account_store.logs[-100:]:
            self.log_box.insert(tk.END, log)

    def run_admin_command(self) -> None:
        try:
            parts = shlex.split(self.command_entry.get().strip())
        except ValueError:
            self.admin_status.set("Invalid command format.")
            return
        if not parts:
            return
        command = parts[0].lstrip("/").lower().replace("-", "_")
        if not self.command_allowed(command):
            self.admin_status.set("Your role cannot use that command.")
            return
        target = self.command_target.get().strip()
        result = self.execute_admin_command(command, target, parts[1:])
        self.admin_status.set(result)
        self.refresh_admin_logs()

    def execute_admin_command(self, command: str, target: str, arguments: list[str]) -> str:
        if command == "logs":
            return "Logs are shown below."
        if command == "creative":
            self.creative_mode = not self.creative_mode
            self.account_store.record(f"{self.username} toggled creative mode {self.creative_mode}")
            return f"Creative mode {'enabled' if self.creative_mode else 'disabled'}."
        if command == "command_block":
            self.command_block_mode = True
            self.account_store.record(f"{self.username} enabled command block mode")
            return "Command block mode enabled. Command blocks are red."
        if command in {"kill", "kick"}:
            target = target or self.username
            if target not in self.account_store.accounts:
                return "Target account was not found."
            self.account_store.record(f"{self.username} used /{command} on {target}")
            return f"/{command} applied to {target}."
        if command in {"tempban", "ban", "permban"}:
            if target == "Jaxon":
                return "The owner cannot be banned."
            if target not in self.account_store.accounts:
                return "Target account was not found."
            if command == "tempban":
                try:
                    days = int(arguments[0]) if arguments else int(self.command_days.get())
                except ValueError:
                    return "Tempban days must be a number."
                if not 1 <= days <= 10:
                    return "OP tempbans must be between 1 and 10 days."
                self.account_store.ban(target, days)
                message = f"{target} tempbanned for {days} day(s)."
            else:
                self.account_store.ban(target, None)
                message = f"{target} permanently banned."
            self.account_store.record(f"{self.username} used /{command} on {target}")
            return message
        if command in {"op", "deop", "superop", "desuperop"}:
            if target not in self.account_store.accounts or target == "Jaxon":
                return "Target account was not found or cannot be changed."
            role = {"op": "op", "deop": "user", "superop": "superop", "desuperop": "user"}[command]
            self.account_store.set_role(target, role)
            self.account_store.record(f"{self.username} used /{command} on {target}")
            return f"{target} is now {role}."
        if command == "delete":
            if target == "Jaxon" or not self.account_store.delete_account(target):
                return "That account cannot be deleted."
            self.account_store.record(f"{self.username} deleted account {target}")
            return f"Account {target} deleted."
        if command == "give":
            item = arguments[0] if arguments else "item"
            self.account_store.record(f"{self.username} gave {target or self.username} {item}")
            return f"Gave {item} to {target or self.username}."
        generic_results = {
            "scan": "Scan complete: hidden severity values are checked.",
            "report": "Report filed in the audit log.",
            "inspect": "Inspection complete: no additional data exposed.",
            "repair": "Repair action queued for the selected target.",
            "heal": "Health restored for the selected target.",
            "teleport": "Teleport request completed.",
            "spawn": "Spawn point loaded.",
            "home": "Home location loaded.",
            "sethome": "Home location saved.",
            "time": "World time checked.",
            "weather": "Weather control executed.",
            "difficulty": "Difficulty setting checked.",
            "gamemode": "Game mode request completed.",
            "effect": "Effect request completed.",
            "clear": "Target inventory cleared.",
            "summon": "Entity summon request completed.",
            "announce": "Announcement sent to the world.",
            "mute": "Target muted.",
            "unmute": "Target unmuted.",
            "warn": "Warning issued to the target.",
            "jail": "Target sent to the holding area.",
            "unjail": "Target released from the holding area.",
            "freeze": "Target movement locked.",
            "unfreeze": "Target movement restored.",
            "spectate": "Spectator view enabled.",
            "vanish": "Visibility disabled.",
            "visible": "Visibility restored.",
            "whitelist": "Whitelist entry updated.",
            "pardon": "Ban record cleared when applicable.",
            "backup": "World backup written.",
            "restore": "World restore request completed.",
            "reload": "World configuration reloaded.",
            "status": f"{self.username}: rank {ROLE_RANK[self.role]}, {self.account_store.capability_count_for(self.username)} capabilities.",
            "profile": f"Profile loaded for {target or self.username}.",
            "rank": f"{self.role.upper()} is rank {ROLE_RANK[self.role]}.",
            "capabilities": f"This rank has {self.account_store.capability_count_for(self.username)} capabilities.",
        }
        result = generic_results.get(command, "Command completed.")
        self.account_store.record(f"{self.username} executed /{command} {target}".rstrip())
        return result

    # endregion
    # endregion

    # region 3D rendering and block interaction

    def draw_world(self) -> None:
        self.world.delete("all")
        width = max(320, self.world.winfo_width())
        height = max(220, self.world.winfo_height())
        horizon = height // 2
        self.world.create_rectangle(0, 0, width, horizon, fill="#79b9d8", outline="")
        self.world.create_rectangle(0, horizon, width, height, fill="#45382e", outline="")
        field_of_view = math.radians(66)
        ray_count = max(120, width // 3)
        for ray_index in range(ray_count):
            camera_x = 2 * ray_index / ray_count - 1
            ray_angle = self.player_angle + math.atan(camera_x * math.tan(field_of_view / 2))
            distance, block_index = self.cast_ray(ray_angle)
            wall_height = min(height * 1.4, height / max(distance, 0.08))
            top = horizon - wall_height / 2
            bottom = horizon + wall_height / 2
            color = self.wall_color(block_index, distance)
            left = ray_index * width / ray_count
            right = (ray_index + 1) * width / ray_count + 1
            self.world.create_rectangle(left, top, right, bottom, fill=color, outline="")
        self.world.create_line(width / 2 - 8, horizon, width / 2 + 8, horizon, fill="#ffffff", width=2)
        self.world.create_line(width / 2, horizon - 8, width / 2, horizon + 8, fill="#ffffff", width=2)
        self.world.create_text(12, 12, anchor="nw", text=f"POS {self.player_x:.1f}, {self.player_y:.1f}   ANG {math.degrees(self.player_angle) % 360:.0f}", fill="white", font=("Segoe UI", 10, "bold"))

    def cast_ray(self, ray_angle: float) -> tuple[float, int | None]:
        step = 0.04
        distance = 0.08
        while distance < max(self.world_columns, self.world_rows) * 2:
            x = self.player_x + math.cos(ray_angle) * distance
            y = self.player_y + math.sin(ray_angle) * distance
            if not (0 <= x < self.world_columns and 0 <= y < self.world_rows):
                return distance, None
            index = int(y) * self.world_columns + int(x)
            player_index = int(self.player_y) * self.world_columns + int(self.player_x)
            if index == player_index:
                distance += step
                continue
            if index not in self.mined_blocks:
                return distance, index
            distance += step
        return distance, None

    def wall_color(self, block_index: int | None, distance: float) -> str:
        if block_index is not None and block_index in self.command_blocks:
            base = (211, 47, 47)
        else:
            material = self.block_materials.get(str(block_index), "stone")
            base = {
                "dirt": (126, 87, 48),
                "stone": (112, 118, 125),
                "cobblestone": (91, 96, 100),
                "wood": (142, 92, 42),
                "brick": (158, 64, 48),
                "glass": (94, 177, 194),
            }.get(material, (112, 94, 72))
        shade = max(0.35, min(1.0, 1.15 / max(distance, 0.3)))
        return "#%02x%02x%02x" % tuple(int(channel * shade) for channel in base)

    def shade_color(self, color: str) -> str:
        return {"#d32f2f": "#a92323", "#866043": "#684a34", "#777f86": "#5b6268"}.get(color, "#337440")

    def dark_color(self, color: str) -> str:
        return {"#d32f2f": "#7f1d1d", "#866043": "#4d3727", "#777f86": "#41474b"}.get(color, "#285d35")

    def block_color(self, value: int | None) -> str:
        if value is None:
            return "#52616b"
        if value >= 8:
            return "#b42318"
        if value >= 4:
            return "#d97706"
        return "#3f8f52"

    def mine_block(self, event: tk.Event) -> None:
        self.mine_facing_block()

    def mine_facing_block(self) -> None:
        index = None
        for distance_step in range(4, 40):
            distance = distance_step / 10
            x = self.player_x + math.cos(self.player_angle) * distance
            y = self.player_y + math.sin(self.player_angle) * distance
            if not (0 <= x < self.world_columns and 0 <= y < self.world_rows):
                break
            candidate = int(y) * self.world_columns + int(x)
            player_index = int(self.player_y) * self.world_columns + int(self.player_x)
            if candidate == player_index:
                continue
            if candidate not in self.mined_blocks:
                index = candidate
                break
        if index is None:
            return
        if not (0 <= index < len(self.blocks)) or index in self.mined_blocks:
            return
        self.selected_block = index
        self.mined_blocks.add(index)
        if self.command_block_mode:
            self.command_blocks.add(index)
            self.block_materials[str(index)] = "command_block"
            self.current_value = None
            self.value_text.set("COMMAND BLOCK")
            self.report_text.set("Red command block placed. Mine another block or disable command block mode.")
            self.status.configure(background="#ffd6d6", foreground="#7f1d1d")
            self.draw_world()
            return
        self.current_value = self.blocks[index]
        self.value_text.set("Severity checked internally")
        loot = RANDOM_THINGS[index % len(RANDOM_THINGS)]
        self.add_item(loot)
        self.report_text.set(f"Block mined. Loot found: {loot}. Report whether this value is a real error.")
        self.status.configure(background="#fff4cc", foreground="#17324d")
        self.draw_world()

    def submit(self, reported_error: bool) -> None:
        if self.current_value is None and self.selected_block is None:
            self.report_text.set("Mine a block before reporting it.")
            return
        actual_error = is_error(self.current_value)
        description = SEVERITY_MESSAGES[self.current_value]

        if reported_error == actual_error:
            self.score += 1
            self.level = 1 + self.score // 3
            self.level_text.set(f"LEVEL {self.level}   SCORE {self.score}")
            self.report_text.set(f"Correct. {self.current_value!r} means {description}. Mine another block.")
            self.status.configure(background="#e8f5e9", foreground="#176b36")
        else:
            self.report_text.set(f"Incorrect. {self.current_value!r} means {description}.")
            self.status.configure(background="#ffebee", foreground="#b42318")

    # endregion

    # region Error challenge

    def open_error_amount_game(self) -> None:
        if self.mini_game_window is not None and self.mini_game_window.winfo_exists():
            self.mini_game_window.lift()
            return

        self.mini_game_window = tk.Toplevel(self.window)
        self.mini_game_window.title("Error Amount Challenge")
        self.mini_game_window.geometry("440x300")
        self.mini_game_window.resizable(False, False)
        self.mini_game_window.protocol("WM_DELETE_WINDOW", self.close_error_amount_game)

        frame = ttk.Frame(self.mini_game_window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="ERROR AMOUNT CHALLENGE", font=("Segoe UI", 14, "bold")).pack()
        ttk.Label(frame, text="How many values below are real errors (4-9)?").pack(pady=(10, 6))

        self.mini_values_text = tk.StringVar()
        ttk.Label(frame, textvariable=self.mini_values_text, font=("Segoe UI", 16, "bold")).pack(pady=4)

        answer_row = ttk.Frame(frame)
        answer_row.pack(pady=10)
        ttk.Label(answer_row, text="Your amount:").pack(side="left", padx=(0, 8))
        self.mini_answer = tk.IntVar(value=0)
        ttk.Spinbox(answer_row, from_=0, to=5, width=5, textvariable=self.mini_answer).pack(side="left")
        ttk.Button(answer_row, text="Report amount", command=self.submit_error_amount).pack(side="left", padx=(8, 0))

        self.mini_status = tk.StringVar()
        ttk.Label(frame, textvariable=self.mini_status, wraplength=390).pack(pady=6)
        ttk.Button(frame, text="New challenge", command=self.new_error_amount_challenge).pack(pady=4)
        self.new_error_amount_challenge()

    def close_error_amount_game(self) -> None:
        if self.mini_game_window is not None:
            self.mini_game_window.destroy()
            self.mini_game_window = None

    def new_error_amount_challenge(self) -> None:
        self.mini_values = [random.choice([None, *range(10)]) for _ in range(5)]
        display_values = ["None" if value is None else str(value) for value in self.mini_values]
        self.mini_values_text.set("   ".join(display_values))
        self.mini_answer.set(0)
        self.mini_status.set("Report the number of real errors in this batch.")

    def submit_error_amount(self) -> None:
        reported_amount = self.mini_answer.get()
        actual_amount = sum(is_error(value) for value in self.mini_values)

        if reported_amount == actual_amount:
            self.mini_score += 1
            self.mini_status.set(
                f"Correct. The real error amount is {actual_amount}. Mini-game score: {self.mini_score}."
            )
        else:
            self.mini_status.set(
                f"Not quite. The real error amount is {actual_amount}. Mini-game score: {self.mini_score}."
            )

    # endregion


# endregion


def main() -> None:
    account_store = AccountStore(Path(__file__).with_name("severity_accounts.json"))
    while True:
        window = tk.Tk()
        window.withdraw()
        login = AccountDialog(window, account_store)
        window.wait_window(login.dialog)
        if login.username is None:
            window.destroy()
            return
        window.deiconify()
        SeverityGame(window, login.username, account_store)
        window.mainloop()


if __name__ == "__main__":
    main()

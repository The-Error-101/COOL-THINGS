import hashlib
import json
import secrets
import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk


BG = "#0b1220"
PANEL = "#111b2e"
PANEL_ALT = "#17243a"
TEXT = "#e9f0ff"
MUTED = "#8392ad"
CYAN = "#52d4e8"
GREEN = "#71e1a5"
AMBER = "#f2bd68"
RED = "#f07878"
LINE = "#263653"


RANKS = {
	1: ("Guest", "No access"),
	2: ("Member", "Limited viewing"),
	3: ("Moderator", "Command execution"),
	4: ("Manager", "Conditional management"),
	5: ("Administrator", "Conditional administration"),
	6: ("Developer", "Conditional code edit"),
	7: ("Co-Owner", "Add / remove control"),
	8: ("Owner", "Full view / edit"),
	9: ("Creator", "Full system control"),
}


@dataclass
class Account:
	username: str
	rank: int
	session: str = "Active"
	pin_hash: str = field(default="")


class JaxonOS(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Jaxon Incorporated OS")
		self.geometry("1260x780")
		self.minsize(1000, 650)
		self.configure(bg=BG)
		self.option_add("*Font", "{Segoe UI} 10")
		self.accounts = self._seed_accounts()
		self.activity = [
			("10:24:41", "Jaxon", "executed full_overwrite", "Terminal"),
			("10:18:32", "Creator", "edited rank permissions", "Console"),
			("10:15:07", "Mod1", "executed safe_command", "Executor"),
			("10:10:55", "Jaxon", "added block: dangerous_command", "Console"),
			("10:08:13", "Jaxon", "promoted Guest1 to Member", "Console"),
		]
		self.blocks = {"dangerous_command", "delete_everything", "raw_database_write"}
		self.current_view = None
		self._setup_styles()
		self._build_shell()
		self.show_dashboard()

	def _seed_accounts(self):
		names = [("Jaxon", 9), ("Creator", 9), ("OpsLead", 8), ("DevOne", 6),
				 ("Admin1", 5), ("Manager1", 4), ("Mod1", 3), ("Member12", 2),
				 ("Guest1", 1)]
		return [Account(name, rank, "Active" if rank >= 3 else "Idle") for name, rank in names]

	def _setup_styles(self):
		style = ttk.Style(self)
		style.theme_use("clam")
		style.configure("Treeview", background=PANEL, foreground=TEXT, fieldbackground=PANEL,
						rowheight=34, borderwidth=0)
		style.map("Treeview", background=[("selected", "#21455a")])
		style.configure("Treeview.Heading", background=PANEL_ALT, foreground=MUTED,
						font=("Segoe UI", 9, "bold"), relief="flat")
		style.configure("TCombobox", fieldbackground=PANEL_ALT, background=PANEL_ALT,
						foreground=TEXT)

	def _build_shell(self):
		self.sidebar = tk.Frame(self, bg="#0d1728", width=235)
		self.sidebar.pack(side="left", fill="y")
		self.sidebar.pack_propagate(False)
		brand = tk.Frame(self.sidebar, bg="#0d1728")
		brand.pack(fill="x", padx=22, pady=(26, 34))
		tk.Label(brand, text="JAXON", bg="#0d1728", fg=TEXT,
				 font=("Segoe UI", 19, "bold")).pack(anchor="w")
		tk.Label(brand, text="INCORPORATED OS", bg="#0d1728", fg=CYAN,
				 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(2, 0))
		tk.Label(brand, text="SYSTEM v2.5.0  /  ONLINE", bg="#0d1728", fg=MUTED,
				 font=("Consolas", 8)).pack(anchor="w", pady=(13, 0))
		self.nav_buttons = {}
		for label, command in [("Overview", self.show_dashboard), ("System Reference", self.show_reference),
							   ("Accounts", self.show_accounts),
							   ("Command Center", self.show_commands), ("Activity Log", self.show_activity),
							   ("Departments", self.show_departments)]:
			self.nav_buttons[label] = self._nav_button(label, command)
		tk.Frame(self.sidebar, bg=LINE, height=1).pack(fill="x", padx=20, pady=24)
		tk.Label(self.sidebar, text="AUTHORITY", bg="#0d1728", fg=MUTED,
				 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=24)
		self._nav_button("Security controls", self.show_security)
		self._nav_button("System settings", self.show_settings)
		self.identity = tk.Frame(self.sidebar, bg="#132b38")
		self.identity.pack(side="bottom", fill="x", padx=14, pady=16)
		tk.Label(self.identity, text="●  JAXON", bg="#132b38", fg=GREEN,
				 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
		tk.Label(self.identity, text="Creator / Level 9 / absolute authority", bg="#132b38", fg=MUTED,
				 font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(3, 12))

		self.main = tk.Frame(self, bg=BG)
		self.main.pack(side="left", fill="both", expand=True)
		self.header = tk.Frame(self.main, bg=BG, height=72)
		self.header.pack(fill="x", padx=34, pady=(20, 0))
		self.header.pack_propagate(False)
		self.page_title = tk.Label(self.header, text="", bg=BG, fg=TEXT,
								   font=("Segoe UI", 22, "bold"))
		self.page_title.pack(side="left", anchor="sw", pady=8)
		self.status_label = tk.Label(self.header, text="●  ALL SYSTEMS OPERATIONAL", bg=BG,
									 fg=GREEN, font=("Segoe UI", 9, "bold"))
		self.status_label.pack(side="right", anchor="sw", pady=13)
		self.content = tk.Frame(self.main, bg=BG)
		self.content.pack(fill="both", expand=True, padx=34, pady=(10, 30))

	def _nav_button(self, label, command):
		button = tk.Button(self.sidebar, text="   " + label, command=command, anchor="w",
						   bg="#0d1728", fg=MUTED, activebackground=PANEL_ALT,
						   activeforeground=TEXT, relief="flat", bd=0, padx=8, pady=10,
						   font=("Segoe UI", 10))
		button.pack(fill="x", padx=14, pady=1)
		return button

	def _clear(self, title):
		for child in self.content.winfo_children():
			child.destroy()
		self.page_title.configure(text=title)
		self.status_label.configure(text="●  ALL SYSTEMS OPERATIONAL", fg=GREEN)

	def _card(self, parent, title, value, detail, color=CYAN):
		card = tk.Frame(parent, bg=PANEL, padx=18, pady=15)
		card.pack(side="left", fill="both", expand=True, padx=(0, 12))
		tk.Label(card, text=title.upper(), bg=PANEL, fg=MUTED,
				 font=("Segoe UI", 8, "bold")).pack(anchor="w")
		tk.Label(card, text=value, bg=PANEL, fg=color,
				 font=("Segoe UI", 25, "bold")).pack(anchor="w", pady=(8, 1))
		tk.Label(card, text=detail, bg=PANEL, fg=MUTED,
				 font=("Segoe UI", 9)).pack(anchor="w")
		return card

	def _section_title(self, parent, text, action=None):
		row = tk.Frame(parent, bg=BG)
		row.pack(fill="x", pady=(24, 10))
		tk.Label(row, text=text, bg=BG, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(side="left")
		if action:
			tk.Button(row, text=action[0], command=action[1], bg=PANEL_ALT, fg=CYAN,
					  activebackground="#21455a", activeforeground=TEXT, relief="flat", bd=0,
					  padx=12, pady=6, font=("Segoe UI", 9, "bold")).pack(side="right")

	def show_dashboard(self):
		self._clear("System overview")
		stats = tk.Frame(self.content, bg=BG)
		stats.pack(fill="x")
		for item in [("Total users", "247", "12 active sessions", CYAN), ("System health", "100%", "All services nominal", GREEN),
					 ("Active ranks", "11", "∞ identity included", AMBER), ("Blocks active", "03", "Policy enforcement live", RED)]:
			self._card(stats, *item)
		body = tk.Frame(self.content, bg=BG)
		body.pack(fill="both", expand=True)
		left = tk.Frame(body, bg=BG)
		left.pack(side="left", fill="both", expand=True, padx=(0, 14))
		self._section_title(left, "Recent activity", ("View all logs", self.show_activity))
		log = tk.Frame(left, bg=PANEL)
		log.pack(fill="both", expand=True)
		for time, actor, action, mode in self.activity:
			row = tk.Frame(log, bg=PANEL, pady=11)
			row.pack(fill="x", padx=16)
			tk.Label(row, text=time, bg=PANEL, fg=MUTED, width=10, anchor="w", font=("Consolas", 9)).pack(side="left")
			tk.Label(row, text=actor, bg=PANEL, fg=TEXT, width=12, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")
			tk.Label(row, text=action, bg=PANEL, fg=TEXT, anchor="w").pack(side="left", fill="x", expand=True)
			tk.Label(row, text=mode, bg=PANEL, fg=CYAN, font=("Segoe UI", 8, "bold")).pack(side="right")
		right = tk.Frame(body, bg=BG, width=250)
		right.pack(side="right", fill="y")
		right.pack_propagate(False)
		self._section_title(right, "Service status")
		service = tk.Frame(right, bg=PANEL, padx=18, pady=8)
		service.pack(fill="x")
		for name, state, color in [("Database", "Online", GREEN), ("Command API", "Online", GREEN),
								   ("Security layer", "Active", CYAN), ("Backups", "Latest", AMBER)]:
			line = tk.Frame(service, bg=PANEL, pady=10)
			line.pack(fill="x")
			tk.Label(line, text=name, bg=PANEL, fg=TEXT).pack(side="left")
			tk.Label(line, text="●  " + state, bg=PANEL, fg=color, font=("Segoe UI", 8, "bold")).pack(side="right")

	def _reference_panel(self, parent, title, accent=CYAN):
		panel = tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
		panel.pack(fill="x", pady=(0, 10))
		tk.Label(panel, text=title.upper(), bg=PANEL, fg=accent,
				 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 7))
		return panel

	def _reference_line(self, parent, label, value, color=TEXT):
		row = tk.Frame(parent, bg=PANEL)
		row.pack(fill="x", padx=12, pady=2)
		tk.Label(row, text=label, bg=PANEL, fg=MUTED, anchor="w").pack(side="left")
		tk.Label(row, text=value, bg=PANEL, fg=color, anchor="e",
				 font=("Segoe UI", 9, "bold")).pack(side="right")

	def show_reference(self):
		self._clear("Complete system reference")
		self.status_label.configure(text="●  REFERENCE MODE  /  ONLINE", fg=CYAN)
		header = tk.Frame(self.content, bg="#101d30", highlightbackground=CYAN, highlightthickness=1)
		header.pack(fill="x", pady=(0, 10))
		identity = tk.Frame(header, bg="#101d30")
		identity.pack(side="left", padx=16, pady=12)
		tk.Label(identity, text="JAXON", bg="#101d30", fg=TEXT,
				 font=("Segoe UI", 18, "bold")).pack(anchor="w")
		tk.Label(identity, text="INCORPORATED  /  COMPLETE SYSTEM REFERENCE", bg="#101d30", fg=CYAN,
				 font=("Segoe UI", 8, "bold")).pack(anchor="w")
		for label, value, color in [("SYSTEM STATUS", "ONLINE", GREEN), ("HIGHEST RANK", "Creator (Level 9)", AMBER),
									("TOTAL ACCOUNTS", "247", TEXT), ("ACTIVE SESSIONS", "12", TEXT), ("VERSION", "2.5.0", CYAN)]:
			cell = tk.Frame(header, bg="#101d30", padx=14, pady=9)
			cell.pack(side="left", fill="y", padx=(0, 1))
			tk.Label(cell, text=label, bg="#101d30", fg=MUTED, font=("Segoe UI", 7, "bold")).pack()
			tk.Label(cell, text=value, bg="#101d30", fg=color, font=("Segoe UI", 9, "bold")).pack(pady=(3, 0))

		columns = tk.Frame(self.content, bg=BG)
		columns.pack(fill="both", expand=True)
		left = tk.Frame(columns, bg=BG, width=280)
		center = tk.Frame(columns, bg=BG, width=300)
		right = tk.Frame(columns, bg=BG, width=300)
		left.pack(side="left", fill="both", expand=True, padx=(0, 7)); center.pack(side="left", fill="both", expand=True, padx=7); right.pack(side="left", fill="both", expand=True, padx=(7, 0))

		panel = self._reference_panel(left, "1. Core purpose", CYAN)
		tk.Label(panel, text="A secure, rank-based system providing complete administrative control, command execution, code management, user management, and full system oversight.\n\nOnly Jaxon (Creator) has absolute authority with full system immunity.", wraplength=245, justify="left", bg=PANEL, fg=TEXT).pack(anchor="w", padx=12, pady=(0, 12))
		panel = self._reference_panel(left, "2. Ranks & numeric mapping", AMBER)
		for level in range(9, 0, -1):
			name, note = RANKS[level]
			row = tk.Frame(panel, bg=PANEL); row.pack(fill="x", padx=12, pady=2)
			tk.Label(row, text=str(level), bg=PANEL, fg=AMBER, width=3, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")
			tk.Label(row, text=name, bg=PANEL, fg=TEXT, width=13, anchor="w").pack(side="left")
			tk.Label(row, text=note, bg=PANEL, fg=MUTED, anchor="w", wraplength=120).pack(side="left")
		panel = self._reference_panel(left, "3. Command modes", GREEN)
		for name, access in [("Terminal:", "Jaxon only"), ("Console:", "Creator + Jaxon"), ("Executor", "Moderator+"), ("Code:", "Master PIN")]:
			self._reference_line(panel, name, access, GREEN)
		tk.Label(panel, text="Higher authority unlocks more execution layers.", bg=PANEL, fg=MUTED).pack(anchor="w", padx=12, pady=(6, 11))

		panel = self._reference_panel(center, "5. System hierarchy overview", CYAN)
		for level in range(9, 0, -1):
			name, note = RANKS[level]
			bar = tk.Frame(panel, bg="#1c3444" if level >= 7 else "#1a2a39", padx=9, pady=5)
			bar.pack(fill="x", padx=12, pady=2)
			tk.Label(bar, text=f"{level:02d}", bg=bar.cget("bg"), fg=AMBER if level >= 7 else GREEN, width=3, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")
			tk.Label(bar, text=name, bg=bar.cget("bg"), fg=TEXT, font=("Segoe UI", 9, "bold")).pack(side="left")
			tk.Label(bar, text=note, bg=bar.cget("bg"), fg=MUTED, anchor="e").pack(side="right")
		panel = self._reference_panel(center, "6. Code ownership rules", AMBER)
		for label, value in [("Creator (Jaxon)", "Owns all code and edits"), ("Owner", "Can edit own code only"), ("Co-Owner", "No code privileges"), ("Others", "No code creation/editing")]:
			self._reference_line(panel, label, value, AMBER)
		panel = self._reference_panel(center, "8. Master PIN enforcement", RED)
		tk.Label(panel, text="ENTER MASTER PIN  [ ****** ]", bg=PANEL, fg=TEXT, font=("Consolas", 9, "bold")).pack(pady=(4, 5))
		tk.Label(panel, text="VERIFY  ->  VALID: EXECUTE + LOG SUCCESS\n          INVALID: ACCESS DENIED + LOG ATTEMPT", bg=PANEL, fg=MUTED, justify="left").pack(anchor="w", padx=12, pady=(0, 11))
		panel = self._reference_panel(center, "9. Command examples", CYAN)
		tk.Label(panel, text="assign_rank(user, rank_number)\nexecute_command(command, args...)\ncreate_command(command, args...)\nblock_feature(feature_name)\nTerminal: overwrite(target, full_access)", bg=PANEL, fg=TEXT, justify="left", font=("Consolas", 8)).pack(anchor="w", padx=12, pady=(0, 12))

		panel = self._reference_panel(right, "10. Account system", CYAN)
		for item in ["Username", "PIN", "Assigned rank", "Privileges", "Session state", "Unique identity"]:
			tk.Label(panel, text="•  " + item, bg=PANEL, fg=TEXT).pack(anchor="w", padx=12, pady=1)
		tk.Label(panel, text="AES-256  |  PBKDF2 + salt  |  RBAC  |  Audit logs\nSession management  |  Brute force protection", bg=PANEL, fg=MUTED, justify="left").pack(anchor="w", padx=12, pady=(7, 11))
		panel = self._reference_panel(right, "11. System overview", GREEN)
		for label, value, color in [("Total users", "247", CYAN), ("Active sessions", "12", CYAN), ("System health", "100%", GREEN), ("Execution layers", "4", AMBER), ("Blocks active", "3", RED)]:
			self._reference_line(panel, label, value, color)
		panel = self._reference_panel(right, "12. Recent activity", AMBER)
		for time, actor, action, mode in self.activity[:5]:
			tk.Label(panel, text=f"{time}  {actor}: {action}", bg=PANEL, fg=TEXT, anchor="w", font=("Consolas", 8)).pack(fill="x", padx=12, pady=2)
		panel = self._reference_panel(right, "13. System controls", RED)
		for item in ["Manage CEO", "Manage all code", "Manage all apps", "Manage everything"]:
			tk.Label(panel, text="▣  " + item, bg=PANEL, fg=RED).pack(anchor="w", padx=12, pady=2)
		tk.Button(panel, text="Open command center  ->", command=self.show_commands, bg="#3a202a", fg=TEXT,
				 activebackground="#572936", relief="flat", bd=0, padx=10, pady=6).pack(anchor="w", padx=12, pady=(7, 11))

	def show_accounts(self):
		self._clear("Account management")
		toolbar = tk.Frame(self.content, bg=BG)
		toolbar.pack(fill="x")
		tk.Button(toolbar, text="+  Create account", command=self.create_account, bg=CYAN, fg=BG,
				  activebackground="#8ee9f4", relief="flat", bd=0, padx=14, pady=8,
				  font=("Segoe UI", 9, "bold")).pack(side="right")
		tk.Label(toolbar, text="RBAC directory  /  rank changes are audit logged", bg=BG, fg=MUTED).pack(side="left", pady=8)
		table = ttk.Treeview(self.content, columns=("user", "rank", "level", "session", "actions"), show="headings")
		for col, heading, width in [("user", "ACCOUNT", 220), ("rank", "RANK", 180), ("level", "LEVEL", 100), ("session", "SESSION", 150), ("actions", "ACCESS", 180)]:
			table.heading(col, text=heading)
			table.column(col, width=width, anchor="w")
		table.pack(fill="both", expand=True, pady=(18, 0))
		for account in self.accounts:
			name, desc = RANKS[account.rank]
			table.insert("", "end", values=(account.username, name, account.rank, account.session,
											   "Full control" if account.rank >= 8 else desc))
		self.account_table = table

	def create_account(self):
		username = simpledialog.askstring("Create account", "Username:", parent=self)
		if not username or any(a.username.lower() == username.lower() for a in self.accounts):
			return
		rank = simpledialog.askinteger("Assign rank", "Rank level (1-8):", parent=self, minvalue=1, maxvalue=8)
		if rank:
			self.accounts.append(Account(username.strip(), rank, "Idle"))
			self._log("Jaxon", f"created account {username.strip()}", "Console")
			self.show_accounts()

	def show_commands(self):
		self._clear("Command center")
		intro = tk.Frame(self.content, bg=PANEL, padx=22, pady=18)
		intro.pack(fill="x")
		tk.Label(intro, text="EXECUTION LAYERS", bg=PANEL, fg=CYAN, font=("Segoe UI", 9, "bold")).pack(anchor="w")
		tk.Label(intro, text="Choose an authorized command channel", bg=PANEL, fg=TEXT,
				 font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(5, 2))
		tk.Label(intro, text="Every execution is validated against rank, blocks, and the audit trail.", bg=PANEL, fg=MUTED).pack(anchor="w")
		grid = tk.Frame(self.content, bg=BG)
		grid.pack(fill="both", expand=True, pady=(18, 0))
		channels = [("Command executor", "Moderator+", "Permitted commands", CYAN, self.safe_command),
					("Console", "Creator + Jaxon", "Rank and permission management", GREEN, self.console_command),
					("Terminal:", "Jaxon only", "Full override authority", RED, self.terminal_command),
					("Code:", "Master PIN required", "Jaxon-only code operations", AMBER, self.code_command)]
		for index, (name, access, desc, color, callback) in enumerate(channels):
			card = tk.Frame(grid, bg=PANEL, padx=20, pady=18)
			card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0, 12 if index % 2 == 0 else 0), pady=(0, 12))
			grid.columnconfigure(index % 2, weight=1); grid.rowconfigure(index // 2, weight=1)
			tk.Label(card, text=name, bg=PANEL, fg=color, font=("Segoe UI", 13, "bold")).pack(anchor="w")
			tk.Label(card, text=access.upper(), bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(5, 12))
			tk.Label(card, text=desc, bg=PANEL, fg=TEXT).pack(anchor="w")
			tk.Button(card, text="Open channel  →", command=callback, bg=PANEL_ALT, fg=TEXT,
					  activebackground="#21455a", relief="flat", bd=0, padx=12, pady=7).pack(anchor="w", pady=(18, 0))

	def safe_command(self):
		command = simpledialog.askstring("Command executor", "Enter a safe command:", parent=self)
		if command:
			if command.lower() in self.blocks:
				messagebox.showerror("Blocked", "This command is blocked by active policy.", parent=self); return
			self._log("Jaxon", f"executed {command}", "Executor")
			messagebox.showinfo("Executed", f"Command accepted: {command}", parent=self)

	def console_command(self):
		self._log("Jaxon", "opened console", "Console")
		messagebox.showinfo("Console", "Console access granted. Rank and policy operations are ready.", parent=self)

	def terminal_command(self):
		target = simpledialog.askstring("Terminal override", "Target to overwrite:", parent=self)
		if target:
			self._log("Jaxon", f"full overwrite on {target}", "Terminal")
			messagebox.showwarning("Override recorded", f"Terminal override recorded for {target}.", parent=self)

	def code_command(self):
		pin = simpledialog.askstring("Master PIN", "Enter Master PIN:", show="*", parent=self)
		if pin == "jaxon-master":
			self._log("Jaxon", "executed protected code operation", "Code")
			messagebox.showinfo("Verified", "Master PIN verified. Protected operation authorized.", parent=self)
		elif pin is not None:
			self._log("Unknown", "failed Master PIN attempt", "Code")
			messagebox.showerror("Access denied", "Invalid Master PIN. Attempt logged.", parent=self)

	def show_activity(self):
		self._clear("Activity log")
		table = ttk.Treeview(self.content, columns=("time", "actor", "event", "channel"), show="headings")
		for col, heading, width in [("time", "TIME", 140), ("actor", "ACTOR", 180), ("event", "EVENT", 520), ("channel", "CHANNEL", 180)]:
			table.heading(col, text=heading); table.column(col, width=width, anchor="w")
		table.pack(fill="both", expand=True)
		for row in self.activity:
			table.insert("", "end", values=row)

	def show_departments(self):
		self._clear("Company departments")
		departments = ["Executive & Governance", "People & HR", "Finance & Accounting", "Operations",
					   "IT & Technology", "Security & Compliance", "Sales & Marketing", "Products & Engineering"]
		left = tk.Frame(self.content, bg=PANEL, width=280); left.pack(side="left", fill="y"); left.pack_propagate(False)
		tk.Label(left, text="AREAS  /  08 OF 100", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=18)
		for number, department in enumerate(departments, 1):
			tk.Button(left, text=f"{number:02d}   {department}", anchor="w", bg=PANEL, fg=TEXT,
					  activebackground=PANEL_ALT, relief="flat", bd=0, padx=18, pady=9).pack(fill="x")
		right = tk.Frame(self.content, bg=BG, padx=28); right.pack(side="left", fill="both", expand=True)
		tk.Label(right, text="IT & Technology", bg=BG, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(20, 5))
		tk.Label(right, text="Infrastructure, applications, and delivery ownership", bg=BG, fg=MUTED).pack(anchor="w")
		for area in ["IT Operations", "Infrastructure", "Applications", "Application Code", "DevOps"]:
			row = tk.Frame(right, bg=PANEL, pady=14, padx=16); row.pack(fill="x", pady=5)
			tk.Label(row, text=area, bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
			tk.Label(row, text="MANAGED  •  SECURE", bg=PANEL, fg=GREEN, font=("Segoe UI", 8, "bold")).pack(side="right")

	def show_security(self):
		self._clear("Security controls")
		self._section_title(self.content, "Active protection policies")
		for title, detail, enabled in [("End-to-end encryption", "AES-256 data protection", True),
									   ("Brute force protection", "Rate limits and lockout policy", True),
									   ("Audit trail", "Every action is timestamped", True),
									   ("Session timeout", "Automatic inactive session expiry", True),
									   ("Integrity monitor", "Anti-tamper verification", True)]:
			row = tk.Frame(self.content, bg=PANEL, padx=18, pady=14); row.pack(fill="x", pady=4)
			tk.Label(row, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
			tk.Label(row, text=detail, bg=PANEL, fg=MUTED).pack(side="left", padx=28)
			tk.Label(row, text="ACTIVE", bg=PANEL, fg=GREEN, font=("Segoe UI", 8, "bold")).pack(side="right")

	def show_settings(self):
		self._clear("System settings")
		tk.Label(self.content, text="Jaxon Incorporated OS", bg=BG, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(20, 5))
		tk.Label(self.content, text="Version 2.5.0  /  Local control plane  /  Identity: Jaxon", bg=BG, fg=MUTED).pack(anchor="w")
		tk.Button(self.content, text="Run integrity check", command=lambda: messagebox.showinfo("Integrity check", "All local system components verified.", parent=self),
				  bg=PANEL_ALT, fg=CYAN, activebackground="#21455a", relief="flat", bd=0, padx=14, pady=9).pack(anchor="w", pady=25)

	def _log(self, actor, event, channel):
		self.activity.insert(0, (datetime.now().strftime("%H:%M:%S"), actor, event, channel))


if __name__ == "__main__":
	app = JaxonOS()
	app.mainloop()

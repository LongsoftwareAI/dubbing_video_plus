"""
UI styling definitions for VoxDub Studio Desktop App — Premium Dark Studio Theme.
Identical palette & typography to VoxDub Studio interface.
"""
DARK_THEME = {
    "bg_window": "#0B0D17",       # Main application dark canvas
    "bg_sidebar": "#111322",      # Left vertical sidebar
    "bg_card": "#181B2E",         # Main cards / container boxes
    "bg_card_inner": "#1E2238",   # Inner section cards
    "bg_terminal": "#0C0E1A",     # Live subtitle log terminal box
    "fg_text": "#F3F4F6",         # Primary white-gray text
    "fg_subtext": "#9CA3AF",      # Muted slate subtext
    "fg_dim": "#6B7280",          # Section header dim text
    "accent": "#4F46E5",          # Indigo primary accent
    "accent_hover": "#6366F1",    # Hover state indigo
    "accent_pill": "#282B48",     # Selected active sidebar item highlight
    "success": "#10B981",         # Emerald green 'xong' status
    "running": "#818CF8",         # Light indigo 'đang chạy' status
    "danger": "#EF4444",          # Red 'Dừng' stop button
    "border": "#252840",          # Card border lines
    "font_family": "Segoe UI"
}

def apply_styles(root):
    """Applies VoxDub Studio premium dark theme to Tkinter root window."""
    try:
        import tkinter as tk
        from tkinter import ttk
        
        root.configure(background=DARK_THEME["bg_window"])
        
        style = ttk.Style(root)
        style.theme_use("clam")
        
        # General Defaults
        style.configure(
            ".",
            background=DARK_THEME["bg_window"],
            foreground=DARK_THEME["fg_text"],
            font=(DARK_THEME["font_family"], 10)
        )
        
        # Frames
        style.configure("TFrame", background=DARK_THEME["bg_window"])
        style.configure("Sidebar.TFrame", background=DARK_THEME["bg_sidebar"])
        style.configure("Card.TFrame", background=DARK_THEME["bg_card"], relief="solid", borderwidth=1, bordercolor=DARK_THEME["border"])
        style.configure("Terminal.TFrame", background=DARK_THEME["bg_terminal"], relief="solid", borderwidth=1, bordercolor=DARK_THEME["border"])
        
        # Labels
        style.configure("TLabel", background=DARK_THEME["bg_window"], foreground=DARK_THEME["fg_text"])
        style.configure("Sidebar.TLabel", background=DARK_THEME["bg_sidebar"], foreground=DARK_THEME["fg_subtext"], font=(DARK_THEME["font_family"], 10))
        style.configure("SidebarActive.TLabel", background=DARK_THEME["accent_pill"], foreground="#FFFFFF", font=(DARK_THEME["font_family"], 10, "bold"))
        style.configure("SidebarSection.TLabel", background=DARK_THEME["bg_sidebar"], foreground=DARK_THEME["fg_dim"], font=(DARK_THEME["font_family"], 9, "bold"))
        
        style.configure("CardTitle.TLabel", background=DARK_THEME["bg_card"], foreground="#FFFFFF", font=(DARK_THEME["font_family"], 11, "bold"))
        style.configure("CardSub.TLabel", background=DARK_THEME["bg_card"], foreground=DARK_THEME["fg_subtext"], font=(DARK_THEME["font_family"], 9))
        
        # Status labels
        style.configure("Success.TLabel", background=DARK_THEME["bg_card"], foreground=DARK_THEME["success"], font=(DARK_THEME["font_family"], 10, "bold"))
        style.configure("Running.TLabel", background=DARK_THEME["bg_card"], foreground=DARK_THEME["running"], font=(DARK_THEME["font_family"], 10, "bold"))
        style.configure("Waiting.TLabel", background=DARK_THEME["bg_card"], foreground=DARK_THEME["fg_dim"], font=(DARK_THEME["font_family"], 10))
        
        # LabelFrames
        style.configure(
            "TLabelframe",
            background=DARK_THEME["bg_card"],
            foreground="#FFFFFF",
            bordercolor=DARK_THEME["border"],
            borderwidth=1,
            relief="solid",
            padding=10
        )
        style.configure(
            "TLabelframe.Label",
            background=DARK_THEME["bg_card"],
            foreground=DARK_THEME["running"],
            font=(DARK_THEME["font_family"], 10, "bold")
        )

        # Primary Buttons
        style.configure(
            "TButton",
            font=(DARK_THEME["font_family"], 10, "bold"),
            background=DARK_THEME["accent"],
            foreground="#FFFFFF",
            padding=[14, 7],
            bordercolor=DARK_THEME["accent"],
            relief="flat"
        )
        style.map(
            "TButton",
            background=[("active", DARK_THEME["accent_hover"]), ("disabled", "#374151")],
            foreground=[("disabled", "#9CA3AF")]
        )

        # Danger / Stop Button
        style.configure(
            "Danger.TButton",
            font=(DARK_THEME["font_family"], 10, "bold"),
            background="#2A1517",
            foreground=DARK_THEME["danger"],
            padding=[16, 8],
            bordercolor=DARK_THEME["danger"],
            relief="solid",
            borderwidth=1
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#3F1D20")]
        )

        # Secondary Button
        style.configure(
            "Secondary.TButton",
            font=(DARK_THEME["font_family"], 9, "bold"),
            background="#252A42",
            foreground="#E5E7EB",
            padding=[10, 5],
            relief="flat"
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#313756")]
        )

        # Combobox & Entry Dark Inputs
        style.configure(
            "TCombobox",
            fieldbackground=DARK_THEME["bg_card_inner"],
            background=DARK_THEME["bg_card_inner"],
            foreground="#FFFFFF",
            bordercolor=DARK_THEME["border"],
            padding=5
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", DARK_THEME["bg_card_inner"])],
            foreground=[("readonly", "#FFFFFF")]
        )

        style.configure(
            "TEntry",
            fieldbackground=DARK_THEME["bg_card_inner"],
            foreground="#FFFFFF",
            bordercolor=DARK_THEME["border"],
            padding=5
        )

        # Notebook / Tabs
        style.configure(
            "TNotebook",
            background=DARK_THEME["bg_window"],
            borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            background=DARK_THEME["bg_card"],
            foreground=DARK_THEME["fg_subtext"],
            padding=[14, 8],
            font=(DARK_THEME["font_family"], 10, "bold"),
            bordercolor=DARK_THEME["bg_window"]
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", DARK_THEME["accent"])],
            foreground=[("selected", "#FFFFFF")]
        )

        # Progressbar
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=DARK_THEME["bg_card"],
            background=DARK_THEME["accent"],
            thickness=10
        )

        # Treeview (Dark Tables)
        style.configure(
            "Treeview",
            background=DARK_THEME["bg_card_inner"],
            fieldbackground=DARK_THEME["bg_card_inner"],
            foreground="#FFFFFF",
            font=(DARK_THEME["font_family"], 9),
            rowheight=28
        )
        style.configure(
            "Treeview.Heading",
            background=DARK_THEME["bg_card"],
            foreground="#FFFFFF",
            font=(DARK_THEME["font_family"], 10, "bold")
        )
        style.map("Treeview", background=[("selected", DARK_THEME["accent"])], foreground=[("selected", "#FFFFFF")])

    except Exception as e:
        print("Dark Style initialization error:", e)

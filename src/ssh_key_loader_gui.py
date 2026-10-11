#!/usr/bin/env python3
import argparse
import configparser
import os
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

APP_ID = "io.github.beckervincent.SshKeyLoader"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ssh-key-loader"
CONFIG_FILE = CONFIG_DIR / "config.ini"
SYSTEM_CONFIG = Path("/etc/ssh-key-loader/config.ini")
AUTOSTART_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "ssh-key-loader.desktop"
DESKTOP_SOURCE = "/usr/share/applications/ssh-key-loader.desktop"

THEME_ORDER = ("oled", "dark", "light", "system")
THEME_LABELS = ("OLED black", "Dark", "Light", "Follow KDE theme")

OLED_CSS = """
window, headerbar, .titlebar {
    background-color: #000000;
}
.boxed-list, .boxed-list > row, .card {
    background-color: #000000;
    border-radius: 12px;
}
popover > contents {
    background-color: #0a0a0a;
    border-radius: 12px;
}
"""


def gather_keys(cfg: configparser.ConfigParser) -> list:
    loot = []
    raw = cfg["key"].get("paths", "").strip()
    if raw:
        loot = [line.strip() for line in raw.splitlines() if line.strip()]
    single = cfg["key"].get("path", "").strip()
    if single and single not in loot:
        loot.insert(0, single)
    return loot


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg["key"] = {"path": "", "paths": "", "add_root": "true"}
    cfg["ui"] = {"theme": "oled", "opacity": "100"}
    for path in (SYSTEM_CONFIG, CONFIG_FILE):
        if path.is_file():
            cfg.read(path)
    if not cfg.has_section("ui"):
        cfg["ui"] = {"theme": "oled", "opacity": "100"}
    return cfg


def window_opacity(cfg: configparser.ConfigParser) -> float:
    try:
        pct = float(cfg["ui"].get("opacity", "100"))
    except ValueError:
        pct = 100.0
    return max(5.0, min(100.0, pct)) / 100.0


def save_config(cfg: configparser.ConfigParser) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w") as scribbler:
        cfg.write(scribbler)


_oled_provider = None


def dress_up_window(theme: str) -> None:
    global _oled_provider
    schemes = {
        "oled": Adw.ColorScheme.FORCE_DARK,
        "dark": Adw.ColorScheme.FORCE_DARK,
        "light": Adw.ColorScheme.FORCE_LIGHT,
        "system": Adw.ColorScheme.DEFAULT,
    }
    Adw.StyleManager.get_default().set_color_scheme(
        schemes.get(theme, Adw.ColorScheme.FORCE_DARK)
    )
    display = Gdk.Display.get_default()
    if display is None:
        return
    if _oled_provider is not None:
        Gtk.StyleContext.remove_provider_for_display(display, _oled_provider)
        _oled_provider = None
    if theme == "oled":
        midnight = Gtk.CssProvider()
        try:
            midnight.load_from_string(OLED_CSS)
        except (AttributeError, TypeError):
            midnight.load_from_data(OLED_CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            display,
            midnight,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        _oled_provider = midnight


def autostart_enabled() -> bool:
    return AUTOSTART_FILE.is_file()


def set_autostart(enabled: bool) -> None:
    if enabled:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=SSH Key Loader\n"
            "Exec=ssh-key-loader\n"
            "Icon=dialog-password\n"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
        AUTOSTART_FILE.write_text(content)
    elif AUTOSTART_FILE.is_file():
        AUTOSTART_FILE.unlink()


def validate_key_passphrase(key_path: str, passphrase: str) -> tuple[bool, str]:
    if not os.path.exists(key_path):
        return False, f"Key file not found: {key_path}"
    try:
        proc = subprocess.run(
            ["ssh-keygen", "-y", "-P", passphrase, "-f", key_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as e:
        return False, f"Error validating passphrase: {e}"

    if proc.returncode == 0:
        return True, ""

    stderr = proc.stderr.strip()
    stderr_lower = stderr.lower()
    if "incorrect passphrase" in stderr_lower:
        return False, "Incorrect passphrase. Please try again."
    elif "bad permissions" in stderr_lower:
        return False, "Private key has insecure permissions (must be 0600)."
    elif "invalid format" in stderr_lower:
        return False, "Invalid private key format."
    elif "no such file" in stderr_lower:
        return False, f"Key file not found: {key_path}"
    else:
        lines = [line.strip() for line in stderr.splitlines() if line.strip()]
        msg = lines[-1] if lines else "Failed to unlock key."
        return False, msg


class PassphraseApp(Adw.Application):
    def __init__(self, key_label: str, key_path: str = ""):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.key_label = key_label
        self.key_path = key_path
        self.result = None

    def do_activate(self):
        cfg = load_config()
        dress_up_window(cfg["ui"].get("theme", "oled"))
        win = Adw.Window(application=self, title="SSH Key Loader",
                         default_width=380, modal=True, resizable=False)
        win.set_opacity(window_opacity(cfg))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=18, margin_bottom=18, margin_start=18, margin_end=18)
        box.append(Gtk.Label(label=f"Passphrase for {self.key_label}", xalign=0))
        entry = Adw.PasswordEntryRow(title="Passphrase")
        rowpile = Gtk.ListBox(css_classes=["boxed-list"])
        rowpile.append(entry)
        box.append(rowpile)

        error_label = Gtk.Label(
            label="",
            wrap=True,
            xalign=0,
            css_classes=["error"],
            visible=False,
        )
        box.append(error_label)

        buttonzoo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                            halign=Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        ok = Gtk.Button(label="Unlock", css_classes=["suggested-action"])
        buttonzoo.append(cancel)
        buttonzoo.append(ok)
        box.append(buttonzoo)
        win.set_content(box)

        def on_changed(*_):
            if entry.has_css_class("error"):
                entry.remove_css_class("error")
                error_label.set_visible(False)

        def accept(*_):
            passphrase = entry.get_text()
            if self.key_path:
                ok_pass, err_msg = validate_key_passphrase(self.key_path, passphrase)
                if not ok_pass:
                    error_label.set_label(err_msg)
                    error_label.set_visible(True)
                    entry.add_css_class("error")
                    entry.error_bell()
                    entry.select_region(0, -1)
                    return
            self.result = passphrase
            win.close()

        cancel.connect("clicked", lambda *_: win.close())
        ok.connect("clicked", accept)
        entry.connect("entry-activated", accept)
        entry.connect("notify::text", on_changed)
        win.present()


class ErrorApp(Adw.Application):
    def __init__(self, message: str):
        super().__init__(application_id=APP_ID + ".Error", flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.message = message

    def do_activate(self):
        cfg = load_config()
        dress_up_window(cfg["ui"].get("theme", "oled"))
        win = Adw.Window(application=self, title="SSH Key Loader",
                         default_width=400, modal=True, resizable=False)
        win.set_opacity(window_opacity(cfg))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                      margin_top=20, margin_bottom=20, margin_start=20, margin_end=20)

        heading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
        icon.set_icon_size(Gtk.IconSize.LARGE)
        heading_box.append(icon)

        lbl_title = Gtk.Label(label="Error loading SSH key", css_classes=["title-3"], xalign=0)
        heading_box.append(lbl_title)
        box.append(heading_box)

        msg_label = Gtk.Label(label=self.message, wrap=True, xalign=0)
        box.append(msg_label)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.END)
        ok_btn = Gtk.Button(label="OK", css_classes=["suggested-action"])
        ok_btn.connect("clicked", lambda *_: win.close())
        btn_box.append(ok_btn)
        box.append(btn_box)

        win.set_content(box)
        win.present()


class SettingsApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID + ".Settings",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)

    def do_activate(self):
        cfg = load_config()
        dress_up_window(cfg["ui"].get("theme", "oled"))
        keychain = gather_keys(cfg)
        win = Adw.PreferencesWindow(application=self, title="SSH Key Loader Settings",
                                    default_width=520, default_height=420, modal=True)
        win.set_opacity(window_opacity(cfg))
        page = Adw.PreferencesPage()

        key_group = Adw.PreferencesGroup(title="Keys",
                                         description="Private keys to load into the agent")
        add_btn = Gtk.Button(label="Add key", valign=Gtk.Align.CENTER,
                             css_classes=["flat"])
        key_group.set_header_suffix(add_btn)
        page.add(key_group)
        stamped_rows = []

        def repaint_keys():
            for stale in stamped_rows:
                key_group.remove(stale)
            stamped_rows.clear()
            if not keychain:
                empty = Adw.ActionRow(title="(no keys selected)")
                key_group.add(empty)
                stamped_rows.append(empty)
                return
            for spot, where in enumerate(keychain):
                row = Adw.ActionRow(title=os.path.basename(where), subtitle=where)
                yeet = Gtk.Button(icon_name="user-trash-symbolic",
                                  valign=Gtk.Align.CENTER, css_classes=["flat"])
                yeet.connect("clicked", lambda _b, i=spot: (keychain.pop(i), repaint_keys()))
                row.add_suffix(yeet)
                key_group.add(row)
                stamped_rows.append(row)

        repaint_keys()

        opt_group = Adw.PreferencesGroup()
        page.add(opt_group)
        root_row = Adw.SwitchRow(title="Also load into root's agent",
                                 subtitle="Asks for elevation once; reuses each passphrase")
        root_row.set_active(cfg["key"].getboolean("add_root", fallback=True))
        opt_group.add(root_row)

        look_group = Adw.PreferencesGroup(title="Appearance")
        page.add(look_group)
        flavors = Gtk.StringList()
        for label in THEME_LABELS:
            flavors.append(label)
        theme_row = Adw.ComboRow(title="Theme", model=flavors)
        current = cfg["ui"].get("theme", "oled")
        theme_row.set_selected(THEME_ORDER.index(current) if current in THEME_ORDER else 0)
        theme_row.connect("notify::selected",
                          lambda r, _p: dress_up_window(THEME_ORDER[r.get_selected()]))
        look_group.add(theme_row)

        op_row = Adw.ActionRow(title="Window opacity",
                               subtitle="Transparency of the windows (5-100%)")
        op_adj = Gtk.Adjustment(lower=5, upper=100, step_increment=5, page_increment=10,
                                value=window_opacity(cfg) * 100)
        op_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=op_adj,
                             draw_value=True, digits=0, hexpand=True, valign=Gtk.Align.CENTER,
                             width_request=240)
        op_scale.connect("value-changed", lambda s: win.set_opacity(s.get_value() / 100.0))
        op_row.add_suffix(op_scale)
        look_group.add(op_row)

        auto_group = Adw.PreferencesGroup(title="Startup")
        page.add(auto_group)
        auto_row = Adw.SwitchRow(title="Run at login")
        auto_row.set_active(autostart_enabled())
        auto_group.add(auto_row)

        win.add(page)

        def on_add(_btn):
            dlg = Gtk.FileDialog(title="Select private key")
            dlg.open(win, None, on_chosen)

        def on_chosen(dlg, res):
            try:
                f = dlg.open_finish(res)
            except Exception:
                return
            if f:
                picked = f.get_path()
                if picked and picked not in keychain:
                    keychain.append(picked)
                    repaint_keys()

        def on_close(*_):
            cfg["key"]["add_root"] = "true" if root_row.get_active() else "false"
            cfg["key"]["paths"] = "\n".join(keychain)
            cfg["key"]["path"] = ""
            cfg["ui"]["theme"] = THEME_ORDER[theme_row.get_selected()]
            cfg["ui"]["opacity"] = str(int(op_adj.get_value()))
            save_config(cfg)
            set_autostart(auto_row.get_active())
            return False

        add_btn.connect("clicked", on_add)
        win.connect("close-request", on_close)
        win.present()


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--settings", action="store_true", help="open settings window")
    parser.add_argument("--error", help="show error dialog with message")
    parser.add_argument("--key-label", default="your SSH key")
    parser.add_argument("--key-path", default="", help="path to private key file")
    args = parser.parse_args()

    if args.settings:
        SettingsApp().run([])
        return 0

    if args.error:
        if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
            sys.stderr.write(f"ssh-key-loader: {args.error}\n")
            return 0
        ErrorApp(args.error).run([])
        return 0

    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        import getpass
        while True:
            try:
                if sys.stdin.isatty():
                    p = getpass.getpass(f"Passphrase for {args.key_label}: ")
                else:
                    line = sys.stdin.readline()
                    if not line:
                        return 1
                    p = line.rstrip("\r\n")
            except (KeyboardInterrupt, EOFError):
                return 1
            if args.key_path:
                ok, err = validate_key_passphrase(args.key_path, p)
                if not ok:
                    sys.stderr.write(f"{err}\n")
                    continue
            sys.stdout.write(p + "\n")
            return 0

    app = PassphraseApp(args.key_label, args.key_path)
    app.run([])
    if app.result is None:
        return 1
    sys.stdout.write(app.result + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

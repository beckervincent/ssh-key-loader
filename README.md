This is a project for my own setup. There are probably nicer ways to do it, but
this is what works for me. Use it if you want. ;)

# ssh-key-loader

Load one or more private SSH keys into `ssh-agent` for your user and,
optionally, for root, typing each passphrase only once.

Built for Fedora KDE but works on most desktops with GTK4 and either polkit or
sudo.

## Install

### Fedora (RPM)

```bash
sudo dnf copr enable beckervincent/ssh-key-loader
sudo dnf install ssh-key-loader
```

Or build locally:

```bash
make lint
sudo make install
```

### Any distro

```bash
sudo make install PREFIX=/usr/local
```

Needs: `python3`, `python3-gobject`, `gtk4`, `libadwaita`, `openssh-clients`,
and polkit or sudo.

## Usage

Configure keys and options:

```bash
ssh-key-loader --settings
```

Then run it (or let it run at login):

```bash
ssh-key-loader
```

Both also show up in the app menu as **SSH Key Loader** and **SSH Key Loader
Settings**.

## Configuration

INI file, system defaults then per-user override:

- `/etc/ssh-key-loader/config.ini`
- `~/.config/ssh-key-loader/config.ini` (written by the settings window)

```ini
[key]
paths =
    /home/you/.ssh/id_ed25519
    /home/you/.ssh/id_rsa
add_root = true

[ui]
theme = oled
opacity = 100
```

- `paths`: one key per indented line. Each is prompted for its own passphrase.
- `add_root`: also load the keys into root's agent.
- `theme`: `oled`, `dark`, `light`, or `system` (follow the KDE theme).
- `opacity`: window transparency in percent, 5 to 100.

`SSH_AUTH_SOCK` is wired into bash, zsh, and fish so later shells and `sudo su`
reuse the same agent.

## Building an RPM

```bash
./packaging/make-tarball.sh
rpmbuild -ba ssh-key-loader.spec
```

## License

MIT, see [LICENSE](LICENSE).

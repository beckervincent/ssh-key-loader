PREFIX  ?= /usr
DESTDIR ?=

BINDIR     = $(DESTDIR)$(PREFIX)/bin
LIBEXECDIR = $(DESTDIR)$(PREFIX)/libexec/ssh-key-loader
APPDIR     = $(DESTDIR)$(PREFIX)/share/applications
DOCDIR     = $(DESTDIR)$(PREFIX)/share/doc/ssh-key-loader
SYSCONFDIR = $(DESTDIR)/etc/ssh-key-loader

.PHONY: all install uninstall lint

all:
	@echo "Nothing to build. Run 'make install' (usually as root)."

install:
	install -d $(BINDIR) $(LIBEXECDIR) $(APPDIR) $(DOCDIR) $(SYSCONFDIR)
	install -m 0755 src/ssh-key-loader            $(BINDIR)/ssh-key-loader
	install -m 0755 src/ssh-key-loader-askpass    $(LIBEXECDIR)/askpass
	install -m 0755 src/ssh_key_loader_gui.py     $(LIBEXECDIR)/gui.py
	install -m 0644 data/ssh-key-loader.desktop          $(APPDIR)/ssh-key-loader.desktop
	install -m 0644 data/ssh-key-loader-settings.desktop $(APPDIR)/ssh-key-loader-settings.desktop
	install -m 0644 data/config.example.ini       $(DOCDIR)/config.example.ini
	test -f $(SYSCONFDIR)/config.ini || install -m 0644 data/config.example.ini $(SYSCONFDIR)/config.ini

uninstall:
	rm -f $(BINDIR)/ssh-key-loader
	rm -rf $(LIBEXECDIR)
	rm -f $(APPDIR)/ssh-key-loader.desktop $(APPDIR)/ssh-key-loader-settings.desktop
	rm -rf $(DOCDIR)

lint:
	bash -n src/ssh-key-loader src/ssh-key-loader-askpass
	PYTHONPYCACHEPREFIX=$${TMPDIR:-/tmp}/pycache python3 -m py_compile src/ssh_key_loader_gui.py

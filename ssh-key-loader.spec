Name:           ssh-key-loader
Version:        1.0.0
Release:        1%{?dist}
Summary:        Load an SSH key into the agent for your user and root, with a dark GTK4 prompt

License:        MIT
URL:            https://github.com/beckervincent/ssh-key-loader
# Sources can be obtained by
# git clone https://github.com/beckervincent/ssh-key-loader
# cd ssh-key-loader
# tito build --tgz
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  make
Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       openssh-clients
Requires:       polkit

%description
ssh-key-loader loads a configured private key into a persistent ssh-agent for
the current user and, optionally, for root. The passphrase is requested once
through a dark GTK4 dialog and reused for both agents, so a later "sudo su"
shell can use the key without re-entering the passphrase. Configuration and
login autostart are managed from a small settings window.

%prep
%autosetup

%build

%install
%make_install PREFIX=%{_prefix}

%files
%license LICENSE
%doc README.md
%{_bindir}/ssh-key-loader
%{_libexecdir}/ssh-key-loader/askpass
%{_libexecdir}/ssh-key-loader/gui.py
%{_datadir}/applications/ssh-key-loader.desktop
%{_datadir}/applications/ssh-key-loader-settings.desktop
%{_docdir}/ssh-key-loader/config.example.ini
%config(noreplace) /etc/ssh-key-loader/config.ini

%changelog
* Wed Jun 10 2026 Vincent Becker <234023680+beckervincent@users.noreply.github.com> - 1.0.0-1
- Initial package.

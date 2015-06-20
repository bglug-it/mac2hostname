Summary: Assigns hostnames based on progressive enumeration
Name: mac2hostname
Version: 2.0.0
Release: 1%{?dist}
URL: https://github.com/bglug-it/mac2hostname/
License: GPLv2+
Group: System Environment/Daemons
BuildRoot: %{_tmppath}/%{name}-root
Requires: python python-bottle
Requires(pre): shadow-utils
Requires(post): chkconfig
Requires(preun): chkconfig initscripts
Requires(postun): shadow-utils initscripts
Source0: mac2hostname-2.0.0.tar.gz
BuildArch: noarch

%description
This is a service that assigns and registers in a database the hostnames to be
assigned on a laboratory inside primary and secondary schools.

%prep
%setup -q

%build

%pre
getent group %{name} >/dev/null || groupadd -r %{name}
getent passwd %{name} >/dev/null || useradd -r -g %{name} -d %{_datadir}/%{name} -s /bin/nologin %{name}

%install
# Installo configurazione
rm -rf %{buildroot}
install -d %{buildroot}
install -d -m 755 %{buildroot}%{_sysconfdir}
install -m 644 mac2hostname.ini %{buildroot}%{_sysconfdir}/%{name}.ini
# Installo il servizio
install -d -m 755 %{buildroot}%{_initrddir}
install -m 755 mac2hostname %{buildroot}%{_initrddir}/%{name}
# Installo lo script vero e proprio
install -d -m 755 %{buildroot}%{_datadir}/%{name}
install -m 755 mac2hostname.py %{buildroot}%{_datadir}/%{name}/mac2hostname.py
# Eseguo comunque un link simbolico
install -d -m 755 %{buildroot}%{_bindir}
ln -sf %{_datadir}/%{name}/mac2hostname.py %{buildroot}%{_bindir}/%{name}
# Cartella del database
install -d %{buildroot}%{_sharedstatedir}/%{name}
# Cartella del log
install -d %{buildroot}%{_localstatedir}/log/%{name}
# Cartella del PID
install -d %{buildroot}%{_localstatedir}/run/%{name}
# Aggiungo servizio al db servizi

%post
/sbin/chkconfig --add %{name}

%preun
if [ "$1" -eq 0 ]; then
	/sbin/service %{name} stop >/dev/null 2>&1
	chkconfig --del %{name}
fi

%postun
/usr/sbin/userdel %{name}

%clean
rm -rf %{buildroot}

%files
%defattr(644,root,root,755)
%doc README.md LICENSE
%config(noreplace) %{_sysconfdir}/mac2hostname.ini
%attr(755,-,-) %{_initrddir}/mac2hostname
%attr(755,-,-) %{_datadir}/mac2hostname/mac2hostname.py
%{_bindir}/mac2hostname

%dir %{_datadir}/%{name}
%dir %attr(755,mac2hostname,mac2hostname) %{_sharedstatedir}/%{name}
%dir %attr(755,mac2hostname,mac2hostname) %{_localstatedir}/log/%{name}
%dir %attr(755,mac2hostname,mac2hostname) %{_localstatedir}/run/%{name}

%changelog
* Sat Jun 20 2015 Emiliano Vavassori <syntaxerrormmm-AT-gmail.com> - 2.0.0-1
- Version 2.0.0 implements a new route for a dynamic inventory for ansible.
- Completely rewritten the daemon and configuration, not anymore compatible withprevious versions.

* Fri Jun 19 2015 Emiliano Vavassori <syntaxerrormmm-AT-gmail.com> - 1.1.0-1
- Added functionality

* Tue Jun 16 2015 Emiliano Vavassori <syntaxerrormmm-AT-gmail.com> - 1.0.0-1
- Release iniziale

#
# spec file for package python-raet
#
# Copyright (c) 2014 SUSE LINUX Products GmbH, Nuernberg, Germany.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via http://bugs.opensuse.org/
#

Name:           python-raet
Version:        0.1.0
Release:        0
License:        Apache-2.0
Summary:        Reliable Asynchronous Event Transport protocol
Url:            https://github.com/saltstack/raet
Group:          Development/Languages/Python
Source0:        https://pypi.python.org/packages/source/r/raet/raet-%{version}.tar.gz
BuildRoot:      %{_tmppath}/raet-%{version}-build

BuildRequires:  python-setuptools
BuildRequires:  python-devel
BuildRequires:  python-six
BuildRequires:  python-ioflo
BuildRequires:  python-libnacl
BuildRequires:  fdupes
BuildRequires:  libsodium-devel
Requires:       python-libnacl
Requires:       python-ioflo

BuildRoot:      %{_tmppath}/%{name}-%{version}-build
%if 0%{?suse_version} && 0%{?suse_version} <= 1110
%{!?python_sitelib: %global python_sitelib %(python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
BuildRequires:  python-importlib
Requires: 		python-importlib
BuildRequires: 	python
Requires: 		python
%else
BuildArch:      noarch
%endif

%description
Raet is a Python library for raet protocol which stands for
Reliable Asynchronous Event Transport protocol.

%prep
%setup -q -n raet-%{version}

%build
python setup.py build

%install
python setup.py install --prefix=%{_prefix} --root=%{buildroot} --optimize=1
%fdupes %{buildroot}%{_prefix}

%files
%defattr(-,root,root)
%{python_sitelib}/*
%{_bindir}/raetflo

%changelog
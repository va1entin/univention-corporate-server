#!/usr/bin/make -f
#
# Univention VirtIO rules file
#
# Copyright 2011-2017 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

SOURCE := virtio-win-0.1.126.iso
TARGET := KVM_Windows_drivers_(virtio_1.1.126).iso

empty :=
space := $(empty) $(empty)
INSTALL ?= install

.PHONY: all
all:

.PHONY: install
install: $(SOURCE)
	$(INSTALL) -m755 -d $(DESTDIR)/usr/share/univention-kvm-virtio
	$(INSTALL) -m644 "$<" "$(DESTDIR)/usr/share/univention-kvm-virtio/$(subst _,$(space),$(TARGET))"

.PHONY: get-orig-source
get-orig-source: $(SOURCE)
virtio-win-%.iso:
	wget -O "$@" "https://updates.software-univention.de/download/large-build-files/virtio/$@"
	echo "b57810f33746ed90420f12f6267903f595ddd02aecb8d3de58cd2d5c0b39ec2f31e0352c2548344e629827616bf2d3c284e1ff60d2132fdde39f2086b36af2e6  $@" | sha512sum -c
	#wget -O "$@" "https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/archive-virtio/virtio-win-$*-1/$@"

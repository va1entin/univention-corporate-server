# -*- coding: utf-8 -*-
#
# Univention LDAP
"""listener script for LDAP ACL extensions."""
#
# Copyright 2013-2014 Univention GmbH
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

__package__ = ''	# workaround for PEP 366
import listener
from univention.config_registry import configHandlers, ConfigRegistry
import univention.debug as ud
import hashlib
import os
import univention.admin.uldap as udm_uldap
import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_errors
import subprocess
import zlib
import tempfile
import datetime
import apt

name = 'settings_ldapacl'
description = 'Configure LDAP ACL extensions'
filter = '(objectClass=univentionLDAPExtensionACL)'
attributes = []

UDM_MODULE = 'settings/ldapacl'
FILE_PREFIX = 'ldapacl_'
UCR_TEMPLATE_DIR = '/etc/univention/templates'
SUBFILE_BASEDIR = '%s/files/etc/ldap/slapd.conf.d' % UCR_TEMPLATE_DIR
INFO_BASEDIR = '%s/info' % UCR_TEMPLATE_DIR

__do_reload = False
__todo_list = []

def handler(dn, new, old):
	"""Handle LDAP ACL extensions on Master, Backup and Slave"""
	global __todo_list, __do_reload

	if not listener.configRegistry.get('ldap/server/type'):
		return

	## Check UCS version requirements first and skip new if they are not met.
	if new:
		univentionUCSVersionStart = new.get('univentionUCSVersionStart', [None])[0]
		univentionUCSVersionEnd = new.get('univentionUCSVersionEnd', [None])[0]
		current_UCR_version = "%s-%s" % ( listener.configRegistry.get('version/version'), listener.configRegistry.get('version/patchlevel') )
		if univentionUCSVersionStart and current_UCR_version < univentionUCSVersionStart:
			ud.debug(ud.LISTENER, ud.INFO, '%s: extension %s requires at least UCR version %s.' % (name, new['cn'][0], univentionUCSVersionStart))
			new=None
		elif univentionUCSVersionEnd and current_UCR_version >= univentionUCSVersionEnd:
			ud.debug(ud.LISTENER, ud.INFO, '%s: extension %s specifies compatibility only up to UCR version %s.' % (name, new['cn'][0], univentionUCSVersionEnd))
			new=None

	if new:
		new_version = new.get('univentionOwnedByPackageVersion', [None])[0]
		if not new_version:
			return

		new_pkgname = new.get('univentionOwnedByPackage', [None])[0]
		if not new_pkgname:
			return

		if old:	## check for trivial changes
			diff_keys = [ key for key in new.keys() if new.get(key) != old.get(key)  and key not in ('entryCSN', 'modifyTimestamp')]
			if diff_keys == ['univentionLDAPACLActive']:
				ud.debug(ud.LISTENER, ud.INFO, '%s: extension %s: activation status changed.' % (name, new['cn'][0]))
				return
			elif diff_keys == ['univentionAppIdentifier']:
				ud.debug(ud.LISTENER, ud.INFO, '%s: extension %s: App identifier changed.' % (name, new['cn'][0]))
				return

			if new_pkgname == old.get('univentionOwnedByPackage', [None])[0]:
				old_version = old.get('univentionOwnedByPackageVersion', ['0'])[0]
				rc = apt.apt_pkg.version_compare(new_version, old_version)
				if rc != 1:
					if not rc in (1, 0, -1):
						ud.debug(ud.LISTENER, ud.ERROR, '%s: Package version comparison to old version failed (%s), skipping update.' % (name, old_version))
					else:
						ud.debug(ud.LISTENER, ud.WARN, '%s: New version is not higher than version of old object (%s), skipping update.' % (name, old_version))
					return
		
		try:
			new_object_data = zlib.decompress(new.get('univentionLDAPACLData')[0], 16+zlib.MAX_WBITS)
		except TypeError:
			ud.debug(ud.LISTENER, ud.ERROR, '%s: Error uncompressing data of object %s.' % (name, dn))
			return

		new_basename = new.get('univentionLDAPACLFilename')[0]
		new_filename = os.path.join(SUBFILE_BASEDIR, new_basename)
		listener.setuid(0)
		try:
			backup_filename = None
			backup_ucrinfo_filename = None
			backup_backlink_filename = None
			if old:
				old_filename = os.path.join(SUBFILE_BASEDIR, old.get('univentionLDAPACLFilename')[0])
				if os.path.exists(old_filename):
					if new_filename == old_filename:
						try:
							with open(old_filename, 'r') as f:
								file_hash = hashlib.sha256(f.read()).hexdigest()
						except IOError:
							file_hash = None
						
						new_hash = hashlib.sha256(new_object_data).hexdigest()
						if new_hash == file_hash:
							ud.debug(ud.LISTENER, ud.INFO, '%s: file %s unchanged.' % (name, old_filename))
							return

					backup_fd, backup_filename = tempfile.mkstemp()
					ud.debug(ud.LISTENER, ud.INFO, '%s: Moving old file %s to %s.' % (name, old_filename, backup_filename))
					try:
						os.rename(old_filename, backup_filename)
					except IOError:
						ud.debug(ud.LISTENER, ud.WARN, '%s: Error renaming old file %s, removing it.' % (name, old_filename))
						os.unlink(old_filename)
						backup_filename = None
						os.close(backup_fd)

				## plus the old backlink file
				old_backlink_filename = "%s.info" % old_filename
				if os.path.exists(old_backlink_filename):
					backup_backlink_fd, backup_backlink_filename = tempfile.mkstemp()
					ud.debug(ud.LISTENER, ud.INFO, '%s: Moving old backlink file %s to %s.' % (name, old_backlink_filename, backup_backlink_filename))
					try:
						os.rename(old_backlink_filename, backup_backlink_filename)
					except IOError:
						ud.debug(ud.LISTENER, ud.WARN, '%s: Error renaming old backlink file %s, removing it.' % (name, old_backlink_filename))
						os.unlink(old_backlink_filename)
						backup_backlink_filename = None
						os.close(backup_backlink_fd)

				## and the old UCR registration
				old_ucrinfo_filename = os.path.join(INFO_BASEDIR, "%s%s.info" % (FILE_PREFIX, old.get('univentionLDAPACLFilename')[0]))
				if os.path.exists(old_ucrinfo_filename):
					backup_ucrinfo_fd, backup_ucrinfo_filename = tempfile.mkstemp()
					ud.debug(ud.LISTENER, ud.INFO, '%s: Moving old UCR info file %s to %s.' % (name, old_ucrinfo_filename, backup_ucrinfo_filename))
					try:
						os.rename(old_ucrinfo_filename, backup_ucrinfo_filename)
					except IOError:
						ud.debug(ud.LISTENER, ud.WARN, '%s: Error renaming old UCR info file %s, removing it.' % (name, old_ucrinfo_filename))
						os.unlink(old_ucrinfo_filename)
						backup_ucrinfo_filename = None
						os.close(backup_ucrinfo_fd)



			if not os.path.isdir(SUBFILE_BASEDIR):
				if os.path.exists(SUBFILE_BASEDIR):
					ud.debug(ud.LISTENER, ud.WARN, '%s: Directory name %s occupied, renaming blocking file.' % (name, SUBFILE_BASEDIR))
					os.rename(SUBFILE_BASEDIR, "%s.bak" % SUBFILE_BASEDIR)
				ud.debug(ud.LISTENER, ud.INFO, '%s: Create directory %s.' % (name, SUBFILE_BASEDIR))
				os.makedirs(SUBFILE_BASEDIR, 0755)

			## Create new extension file
			try:
				ud.debug(ud.LISTENER, ud.INFO, '%s: Writing new extension file %s.' % (name, new_filename))
				with open(new_filename, 'w') as f:
					f.write(new_object_data)
			except IOError:
				ud.debug(ud.LISTENER, ud.ERROR, '%s: Error writing file %s.' % (name, new_filename))
				return

			## plus backlink file
			try:
				new_backlink_filename = "%s.info" % new_filename
				ud.debug(ud.LISTENER, ud.INFO, '%s: Writing backlink file %s.' % (name, new_backlink_filename))
				with open(new_backlink_filename, 'w') as f:
					f.write("%s\n" % dn)
			except IOError:
				ud.debug(ud.LISTENER, ud.ERROR, '%s: Error writing backlink file %s.' % (name, new_backlink_filename))
				return

			## and UCR registration
			try:
				new_ucrinfo_filename = os.path.join(INFO_BASEDIR, "%s%s.info" % (FILE_PREFIX, new.get('univentionLDAPACLFilename')[0]))
				ud.debug(ud.LISTENER, ud.INFO, '%s: Writing UCR info file %s.' % (name, new_ucrinfo_filename))
				with open(new_ucrinfo_filename, 'w') as f:
					f.write("Type: multifile\nMultifile: etc/ldap/slapd.conf\n\nType: subfile\nMultifile: etc/ldap/slapd.conf\nSubfile: etc/ldap/slapd.conf.d/%s\n" % new_basename)
			except IOError:
				ud.debug(ud.LISTENER, ud.ERROR, '%s: Error writing UCR info file %s.' % (name, new_ucrinfo_filename))
				return

			## Commit to slapd.conf
			ucr = ConfigRegistry()
			ucr.load()
			ucr_handlers = configHandlers()
			ucr_handlers.load()
			ucr_handlers.commit(ucr, ['/etc/ldap/slapd.conf'])

			## validate
			p = subprocess.Popen(['/usr/sbin/slaptest', '-u'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
			stdout, stderr = p.communicate()
			if p.returncode != 0:
				ud.debug(ud.LISTENER, ud.ERROR, '%s: slapd.conf validation failed:\n%s.' % (name, stdout))
				## Revert changes
				ud.debug(ud.LISTENER, ud.ERROR, '%s: Removing new file %s.' % (name, new_filename))
				os.unlink(new_filename)
				os.unlink(new_backlink_filename)
				os.unlink(new_ucrinfo_filename)
				if backup_filename:
					ud.debug(ud.LISTENER, ud.ERROR, '%s: Restoring previous file %s.' % (name, old_filename))
					try:
						os.rename(backup_filename, old_filename)
						os.close(backup_fd)
					except IOError:
						ud.debug(ud.LISTENER, ud.ERROR, '%s: Error reverting to old file %s.' % (name, old_filename))
				## plus backlink file
				if backup_backlink_filename:
					ud.debug(ud.LISTENER, ud.ERROR, '%s: Restoring previous backlink file %s.' % (name, old_backlink_filename))
					try:
						os.rename(backup_backlink_filename, old_backlink_filename)
						os.close(backup_backlink_fd)
					except IOError:
						ud.debug(ud.LISTENER, ud.ERROR, '%s: Error reverting to old backlink file %s.' % (name, old_backlink_filename))
				## and the old UCR registration
				if backup_ucrinfo_filename:
					ud.debug(ud.LISTENER, ud.ERROR, '%s: Restoring previous UCR info file %s.' % (name, old_ucrinfo_filename))
					try:
						os.rename(backup_ucrinfo_filename, old_ucrinfo_filename)
						os.close(backup_ucrinfo_fd)
					except IOError:
						ud.debug(ud.LISTENER, ud.ERROR, '%s: Error reverting to old UCR info file %s.' % (name, old_ucrinfo_filename))
				## Commit and exit
				ucr_handlers.commit(ucr, ['/etc/ldap/slapd.conf'])
				return
			ud.debug(ud.LISTENER, ud.INFO, '%s: validation successful.' % (name,))

			## cleanup backup
			if backup_filename:
				ud.debug(ud.LISTENER, ud.INFO, '%s: Removing backup of old file %s.' % (name, backup_filename))
				os.unlink(backup_filename)
				os.close(backup_fd)
			## plus backlink file
			if backup_backlink_filename:
				ud.debug(ud.LISTENER, ud.INFO, '%s: Removing backup of old backlink file %s.' % (name, backup_backlink_filename))
				os.unlink(backup_backlink_filename)
				os.close(backup_backlink_fd)
			## and the old UCR registration
			if backup_ucrinfo_filename:
				ud.debug(ud.LISTENER, ud.INFO, '%s: Removing backup of old UCR info file %s.' % (name, backup_ucrinfo_filename))
				os.unlink(backup_ucrinfo_filename)
				os.close(backup_ucrinfo_fd)

			__todo_list.append(dn)
			__do_reload = True

		finally:
			listener.unsetuid()
	elif old:
		old_filename = os.path.join(SUBFILE_BASEDIR, old.get('univentionLDAPACLFilename')[0])
		## plus backlink file
		old_backlink_filename = "%s.info" % old_filename
		## and the old UCR registration
		old_ucrinfo_filename = os.path.join(INFO_BASEDIR, "%s%s.info" % (FILE_PREFIX, old.get('univentionLDAPACLFilename')[0]))
		if os.path.exists(old_filename):
			listener.setuid(0)
			try:
				ud.debug(ud.LISTENER, ud.INFO, '%s: Removing extension %s.' % (name, old['cn'][0]))
				if os.path.exists(old_ucrinfo_filename):
					os.unlink(old_ucrinfo_filename)
				if os.path.exists(old_backlink_filename):
					os.unlink(old_backlink_filename)
				os.unlink(old_filename)

				ucr = ConfigRegistry()
				ucr.load()
				ucr_handlers = configHandlers()
				ucr_handlers.load()
				ucr_handlers.commit(ucr, ['/etc/ldap/slapd.conf'])

				__do_reload = True
				if dn in __todo_list:
					__todo_list = [ x for x in __todo_list if x != dn ]
					if not __todo_list:
						__do_reload = False

			finally:
				listener.unsetuid()

def postrun():
	"""Restart LDAP server Master and mark new extension objects active"""
	global __todo_list, __do_reload

	## Only set active flag on Master
	if not listener.configRegistry.get('server/role') == 'domaincontroller_master':
		__todo_list = []

	initscript='/etc/init.d/slapd'
	if os.path.exists(initscript):
		listener.setuid(0)
		try:
			if __do_reload:
				ud.debug(ud.LISTENER, ud.INFO, '%s: Reloading LDAP server.' % (name,) )
				p = subprocess.Popen([initscript, 'graceful-restart'], close_fds=True)
				p.wait()
				__do_reload = False
				if p.returncode != 0:
					ud.debug(ud.LISTENER, ud.ERROR, '%s: LDAP server restart returned %s.' % (name, p.returncode))
					return

			if __todo_list:
				try:
					lo, ldap_position = udm_uldap.getAdminConnection()
					udm_modules.update()
					udm_module = udm_modules.get(UDM_MODULE)
					udm_modules.init(lo, ldap_position, udm_module)

					for object_dn in __todo_list:
						try:
							udm_object = udm_module.object(None, lo, ldap_position, object_dn)
							udm_object.open()
							udm_object['active']=True
							udm_object.modify()
						except udm_errors.ldapError, e:
							ud.debug(ud.LISTENER, ud.ERROR, '%s: Error modifying %s: %s.' % (name, object_dn, e))
					__todo_list = []

				except udm_errors.ldapError, e:
					ud.debug(ud.LISTENER, ud.ERROR, '%s: Error accessing UDM: %s' % (name, e))

		finally:
			listener.unsetuid()


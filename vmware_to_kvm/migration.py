#!/usr/bin/python
#_*_ coding=utf-8

import os
import sys
import yaml
import subprocess
from shade import exc
from shade import openstack_cloud


from oslo_config import cfg



CONF = cfg.CONF


opts_common = [
	cfg.StrOpt('vcenter_host',
			   default='0.0.0.0',
			   help="vcenter host ip or hostname"),
	cfg.StrOpt('vcenter_user',
			   default='animistrator',
			   help='vcenter super_user'),
	cfg.StrOpt('password_file',
			   default='password',
			   help="vcenter superuser password"),
	cfg.StrOpt('Datacenter_url',
			   default='datacenter',
			   help='datacenter'),
	cfg.StrOpt('esxi_host',
			   default='0.0.0.0',
			   help='esxi_host'),
	cfg.StrOpt('LIBGUESTFS_BACKEND',
			   default='direct',
			   help='LIBGUESTFS_BACKEND')
]

opts_keystone = [
	cfg.StrOpt('OS_PROJECT_DOMAIN_ID',
			   default='default',
			   help="project_domian_id"),
	cfg.StrOpt('OS_USER_DOMAIN_ID',
			   default='default',
			   help="OS_USER_DOMAIN_ID"),
	cfg.StrOpt('OS_PROJECT_NAME',
			   default='admin',
			   help="OS_PROJECT_NAME"),
	cfg.StrOpt('OS_USERNAME',
			   default='admin',
			   help="OS_USERNAME"),
	cfg.StrOpt('OS_PASSWORD',
			   default='admin',
			   help='OS_PASSWORD'),
	cfg.StrOpt('OS_AUTH_URL',
			   default='http://172.16.214.81:35357/v3',
			   help='OS_AUTH_URL'),
	cfg.StrOpt('OS_IDENTITY_API_VERSION',
			   default='3',
			   help='3'),
	cfg.StrOpt('OS_COMPUTE_API_VERSION',
			   default='2.5',
			   help='OS_COMPUTE_API_VERSION'),
]

possible_actions = [
	cfg.StrOpt('action',
	           default='list',
	           choices=['list', 'migrate'],
	           help="choice action list or migrate"),
	cfg.StrOpt('vm_host',
	           default='',
	           help="vm host name")
]

def set_env():
	env = {
		'OS_PROJECT_DOMAIN_ID': CONF.keystone_auth.OS_PROJECT_DOMAIN_ID,
		'OS_USER_DOMAIN_ID': CONF.keystone_auth.OS_PROJECT_DOMAIN_ID,
		'OS_PROJECT_NAME': CONF.keystone_auth.OS_PROJECT_NAME,
		'OS_USERNAME': CONF.keystone_auth.OS_USERNAME,
		'OS_PASSWORD': CONF.keystone_auth.OS_PASSWORD,
		'OS_AUTH_URL': CONF.keystone_auth.OS_PASSWORD,
		'OS_IDENTITY_API_VERSION': CONF.keystone_auth.OS_IDENTITY_API_VERSION,
		'OS_AUTH_VERSION': CONF.keystone_auth.OS_IDENTITY_API_VERSION,
		'OS_COMPUTE_API_VERSION' : CONF.keystone_auth.OS_COMPUTE_API_VERSION,
		'LIBGUESTFS_BACKEND': CONF.LIBGUESTFS_BACKEND
	}
	return os.environ.update(env)

class VmwareCheck(object):

	def __init__(self, migration_esxi):
		self.migration_esxi = migration_esxi

	def list_vms(self):
		virt_command = "virsh -c '{0}' list --all".format(self.migration_esxi)
		try:
			subprocess.call(virt_command,
						 	stdout=sys.stdout,
						 	shell=True)
		except Exception as e:
			raise Exception(e)

	def migration_vm(self, esxi_url, vm):
		"""
		无法使用虚拟环境加载 virt-v2v 后期调试
		env = {"OS_AUTH_URL": "http://node-25:35357/v3",
			   "OS_AUTH_VERSION": "3",
			   "OS_COMPUTE_API_VERSION": "2.5",
			   "OS_IDENTITY_API_VERSION": "3",
			   "OS_PASSWORD": "admin",
			   "OS_PROJECT_DOMAIN_ID": "default",
			   "OS_PROJECT_NAME": "admin",
			   "OS_USERNAME": "admin",
			   "LIBGUESTFS_BACKEND": "direct",
			   "OS_USER_DOMAIN_ID": "default"}

		migration_command = "virt-v2v -v -x -ic %s %s -o glance -of qcow2 --password-file %s" \
								% (esxi_url, vm, CONF.password_file)

		subprocess.Popen(migration_command,
						 stdout=sys.stdout,
						 shell=True,
						 env=env)
		"""
		migration_command = "virt-v2v -v -x -ic %s %s -o local -os /virt/vm -of qcow2 --password-file %s" \
							% (esxi_url, vm, CONF.password_file)
		subprocess.call(migration_command,
						stdout=sys.stdout,
						shell=True)

class OpenStackAPI(object):

	def __init__(self, cloud):
		self._cloud = cloud
		self._conn = self._get_conn()

	def _get_conn(self):
		conn = openstack_cloud(cloud=self._cloud)
		return conn

	def create_image(self, name,
					 filename=None,
					 md5=None, sha256=None,
					 disk_format=None,
					 container_format=None,
					 disable_vendor_agent=True,
					 wait=False,
					 timeout=4800,
					 allow_duplicates=True,
					 meta=None, ):
		try:
			img = self._conn.create_image(name=name,
										  filename=filename,
										  md5=md5, sha256=sha256,
										  disk_format=disk_format,
										  container_format=container_format,
										  disable_vendor_agent=disable_vendor_agent,
										  wait=wait,
										  timeout=timeout,
										  allow_duplicates=allow_duplicates,
										  meta=meta,)
			return img
		except exc.OpenStackCloudException as e:
			print "create image {0} failed, error msg: {1}".format(name, e)
	
	def create_server(self):
		print "Not implementation"


def load_config(config_file):
	with open(config_file, 'r') as f:
		return yaml.load(f)



def config(args=[]):
	CONF.register_opts(opts_common, group='DEFAULT')
	CONF.register_opts(opts_keystone, group='keystone_auth')
	CONF.register_cli_opts(opts_common)  #开启命令行方式写参数
	CONF.register_cli_opts(possible_actions)
	CONF.register_cli_opts(opts_keystone) #开启命令行方式写参数
	default_conf = cfg.find_config_files('migration')
	CONF(args=args,
		 project='migration',
		 default_config_files=default_conf)

def main():
	config(args=sys.argv[1:])
	#config(args=[])
	set_env()
	config_data = load_config('clouds.yml')
	cloud = 'myfavoriteopenstack'
	client = OpenStackAPI(cloud=cloud)

	if not config_data:
		print "no config data has been loaded"
		sys.exit(1)

	if len(sys.argv) < 2:
		CONF.print_help()
		sys.exit(1)
	user = CONF.vcenter_user
	vcenter_host = CONF.vcenter_host
	Datacenter_url = CONF.Datacenter_url
	esxi_host = CONF.esxi_host
	esxi_path = os.path.join(vcenter_host, Datacenter_url,
							 esxi_host)
	esxi_url = "vpx://%s@%s?no_verify=1" % (user, esxi_path)
	vmware = VmwareCheck(esxi_url)
	
	if CONF.action == 'list':
		vmware.list_vms()
	if CONF.action == 'migrate':
		vm_host = CONF.vm_host
		vmware.migration_vm(esxi_url, vm_host)
		filename = os.path.join('/virt/vm',
								vm_host +'-sda')
		client.create_image(name=vm_host,
							filename=filename,
							disk_format='qcow2',
							container_format='bare'
							)

if __name__ == '__main__':
	sys.exit(main())

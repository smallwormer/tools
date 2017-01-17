#!/usr/bin/python
#_*_ coding=utf-8


from mako import exceptions
from mako.lookup import TemplateLookup
from multiprocessing import Pool
from shade import exc
from shade import openstack_cloud
import os
import sys
import time
import xlrd
import yaml


class GetExcelData(object):

    def __init__(self, path):
        self.path = path

    def check_sheet_available(self, i):
        if i.cell_value(8, 3) != "" and i.cell_value(12, 1) != "":
            return True

    def read_excel_data(self):
        """
        :return: data object
        """
        data = None
        try:
            data = xlrd.open_workbook(self.path)
            return data
        except Exception, e:
            print str(e)


    def mapping_vlan_project(self):
        """
        :return: mapping vlan and project
        """

        vlan_project = {
            "VLAN153": "Development",
            "VLAN154": "Testing"
        }
        return vlan_project

    def get_param_from_excel(self):
        return self.__get_param_from_excel()

    def __get_param_from_excel(self):
        """

        :return: [{'Development': {"ss": "sss"}}，{'Testing': {"ss": "sss"}}]
        """
        param_list = []
        data = self.read_excel_data()
        print data

        def check_project_same(data):
            projects = {}
            for i in data.sheets():
                net = i.cell_value(8, 1)
                if net:
                    projects[i.name] = str(net.split('(')[-1].split(')')[0])
            # projects = {'sheet1': 'vlan153', "sheet2": "vlan154", "sheet3": "VLAN153"}

            vlan_project = {
                "VLAN153": "Development",
                "VLAN154": "Testing"
            }

            sheet_project = []
            for i in projects:
                if projects[i] in vlan_project.keys():
                    project ={}
                    project[vlan_project[projects[i]]] = i
                    sheet_project.append(project)
            return sheet_project

        sheet_project = check_project_same(data)
        print sheet_project
        for num in range(len(sheet_project)):
            for key in sheet_project[num]:
                i = data.sheet_by_name(sheet_project[num][key])
                if self.check_sheet_available(i):
                    param_dict = {}
                    params_list_sub = {}
                    image = i.cell_value(13, 1)
                    flavor = i.cell_value(12, 1)
                    instance_user_name = i.cell_value(4, 1)
                    net = i.cell_value(8, 1)
                    vol_size = i.cell_value(14, 1)
                    volume_nums = i.cell_value(14, 3)
                    volume_desc = i.cell_value(10, 1)
                    instances_nums = i.cell_value(8, 3)
                    stack_name = i.cell_value(9, 1)
                    param_dict['image'] = str(image)
                    param_dict['flavor'] = str(flavor)
                    param_dict['volume_desc'] = str(volume_desc.encode('utf-8'))
                    param_dict['net'] = str(net.split('(')[-1].split(')')[0])
                    param_dict['volume_nums'] = int(volume_nums if volume_nums else 0)
                    param_dict['vol_size'] = int(vol_size if vol_size else 0)
                    param_dict['instances_nums'] = int(instances_nums)
                    param_dict['stack_name'] = str(instance_user_name+ '-' +stack_name)
                    params_list_sub[key] = param_dict
                    param_list.append(params_list_sub)

        return param_list



class OpenStackAPI(object):

    def __init__(self, cloud):
        self.__cloud = cloud
        self.__conn = self.__get_conn()

    def __get_conn(self):
        conn = openstack_cloud(cloud=self.__cloud)
        return conn

    def create_stack(
            self, name,
            template_file=None, template_url=None,
            template_object=None, files=None,
            rollback=True,
            wait=False, timeout=3600,
            environment_files=None,
            **parameters):
        print "*****  begin create heat stack {}  *****".format(name)
        self.__conn.create_stack(name=name,
                                 template_file=template_file,
                                 template_url=template_url,
                                 template_object=template_object,
                                 files=files,
                                 rollback=rollback,
                                 wait=wait,
                                timeout=timeout,
                                environment_files=environment_files,
                                **parameters)
        print "*****  finish create heat stack {}  *****".format(name)

def paralley_create_stack(cloud,
                          name,
                          template_file,
                          wait=True):
    client = OpenStackAPI(cloud=cloud)
    try:

        client.create_stack(name=name,
                            template_file=template_file,
                            wait=wait)
    except exc.OpenStackCloudException as e:
        print "create heat stack {0} failed, error msg: {1}".format(name, e)

def generate_heat_template(params_list=[]):
    templates_dir = 'heat/mako_templates'
    templates_cache = 'heat/cache'
    output_templates_dir = 'heat/templates'

    templates_list = []

    env = TemplateLookup(directories=[templates_dir],
                         module_directory=templates_cache,
                         output_encoding='utf-8',
                         encoding_errors='replace')
    tpl_list = os.listdir(templates_dir)
    for t in tpl_list:
        try:
            tpl = env.get_template(t)
            for param_project in params_list:
                param_dict_value = param_project.values()[0]
                output = tpl.render(**param_dict_value)
                template_name = (time.strftime('%y-%m-%d') +
                                 '_' +
                                 param_dict_value.get('stack_name') +
                                 '_' + param_project.keys()[0] +
                                 os.path.basename(t))

                template_path = os.path.join(output_templates_dir,
                                             template_name)
                if os.path.exists(output_templates_dir) == False:
                    os.makedirs(output_templates_dir)
                with open(template_path, 'w') as out:
                    out.write(output)
                templates_list.append((param_dict_value.get('stack_name'),
                                       template_path, param_project.keys()[0]))
        except:
            print (exceptions.text_error_template().render())
    return templates_list

def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.load(f)

if __name__ == '__main__':
    path_xlsx = sys.argv[1]
    config_data = load_config('clouds.yml')
    if not config_data:
        print "No config data has been loaded"
        sys.exit(1)
    xlxs = GetExcelData(path_xlsx)
    params_list = xlxs.get_param_from_excel()
    templates_list = generate_heat_template(params_list=params_list)
    print templates_list
    pool = Pool(20)
    for name, template_file, project in templates_list:
        cloud = project
        pool.apply_async(paralley_create_stack,
                         args=(cloud,
                               name,
                               template_file,
                               ))
    pool.close()
    pool.join()

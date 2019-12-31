#!/usr/bin/env python
#coding=utf-8

import datetime
import json
import matplotlib.pyplot as plt
import numpy as np
import time
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526.DescribeSpotPriceHistoryRequest import DescribeSpotPriceHistoryRequest
from aliyunsdkecs.request.v20140526.RunInstancesRequest import RunInstancesRequest
from aliyunsdkecs.request.v20140526.DescribeImagesRequest import DescribeImagesRequest
from aliyunsdkecs.request.v20140526.DescribeInstanceTypesRequest import DescribeInstanceTypesRequest
from aliyunsdkecs.request.v20140526.DescribeSecurityGroupsRequest import DescribeSecurityGroupsRequest
from aliyunsdkecs.request.v20140526.DescribeVSwitchesRequest import DescribeVSwitchesRequest
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526.DeleteInstanceRequest import DeleteInstanceRequest

AccessKeyID = '<access-key-id>'
AccessKeySecret = '<access-key-secret>'

# 地域
# https://help.aliyun.com/knowledge_detail/40654.html
regionList = [
    ['深圳', 'cn-shenzhen'],
    ['杭州', 'cn-hangzhou'],
    ['香港', 'cn-hongkong'],
    ['上海', 'cn-shanghai'],
]

# 实例规格族
typeList = ['xn4', 'e4', 'n4', 'mn4'] #, 'n4', 'mn4', 'e3', 'n1', 'n2'

def selectOption(tips, option, printOut = True):
    ### 选择可选项 ###
    if printOut:
        for k, v in enumerate(option):
            print("%-3s" % str(k + 1), v[0])
    while True:
        arg = int(input(tips)) - 1
        if arg >=0 and arg < len(option):
            break
    if len(option[arg]) == 2: 
        return option[arg][1]
    else:
        return arg



# 选择操作
action = selectOption('选择操作：', [
    ['对比价格'],
    ['创建实例'],
    ['查看实例'],
    ['释放实例'],
])
print()

option = []

if action == 0:
    
    # 选择地域
    client = AcsClient(AccessKeyID, AccessKeySecret, 'cn-hangzhou')
    print()
    cpu = input('CPU核数：')
    memory = input('内存大小(G)：')
    gpu = input('GPU核数：')
    if cpu == '':
        cpu = 0
    if memory == '':
        memory = 0
    if gpu == '':
        gpu = 0
    cpu = int(cpu)
    memory = int(memory)
    gpu = int(gpu)

    print("No\tCPU\tMemory\tGPU\tBandwidth\tPps\tInstanceTypeId")
    # for i in typeList:
    # 查看InstanceTypeFamily下的规格
    request = DescribeInstanceTypesRequest()
    request.set_accept_format('json')
    # request.set_InstanceTypeFamily('ecs.' + i)

    response = client.do_action_with_exception(request)
    response = json.loads(response)
    # print(json.dumps(response,indent=2))
    for item in response['InstanceTypes']['InstanceType']:
        if cpu!=0 and item['CpuCoreCount'] != cpu:
            continue
        if memory!=0 and item['MemorySize'] != memory:
            continue
        if gpu!=0 and item['GPUAmount'] != gpu:
            continue
        if 'InstanceBandwidthRx' not in item:
            item['InstanceBandwidthRx'] = 0
        if 'InstancePpsRx' not in item:
            item['InstancePpsRx'] = 0
        option.append([
            "\t" + 
            str(item['CpuCoreCount']) + "\t" + 
            str(int(item['MemorySize'])) + "\t" + 
            str(item['GPUAmount']) + "\t" + 
            str(item['InstanceBandwidthRx']/1024000)+'k' + "\t\t" + 
            str(int(item['InstancePpsRx']/10000))+'W' + "\t" +
            str(item['InstanceTypeId']), 
            str(item['InstanceTypeId'])
        ])
    # exit()
    instanceType = selectOption('选择规格No：', option)
    print(instanceType)
    print()
    while True:

        typePriceList = {}
        start = time.time()
        zoneMinList = {}
        for region in regionList:
            client = AcsClient(AccessKeyID, AccessKeySecret, region[1])

            # 查看抢占式实例近30日价格

            # start1 = time.time()
            request = DescribeSpotPriceHistoryRequest()
            request.set_accept_format('json')

            request.set_NetworkType("vpc")
            request.set_InstanceType(instanceType)
            # day30 = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            # request.set_StartTime(day30)

            response = client.do_action_with_exception(request)
            # print(time.time()-start1, 's')
            # print(json.dumps(json.loads(response),indent=2))
            response = json.loads(response)
            if not response['SpotPrices']['SpotPriceType']:
                continue
            priceDetail = {}
            for i in response['SpotPrices']['SpotPriceType']:
                if i['ZoneId'] in priceDetail:
                    priceDetail[i['ZoneId']].append(i['SpotPrice'])
                else:
                    priceDetail[i['ZoneId']] = [i['SpotPrice']]
            priceTotal = []
            for i in priceDetail:
                priceTotal.append([i, priceDetail[i][-1], sum(priceDetail[i])/len(priceDetail[i])])
            # priceTotal = {
            #           现价    均价
            #     'a':[0.016, 0.0161],
            #     'b':[0.016, 0.016],
            #     'c':[0.016, 0.0162],
            #     'd':[0.018, 0.014],
            #     'e':[0.016, 0.015],
            # }
            # print(priceTotal)
            # exit()
            priceTotal.sort(key=lambda d: (d[1], d[2]))
            if instanceType in typePriceList:
                typePriceList[instanceType].append([region[1], priceTotal[0][0], priceTotal[0][1]])
            else:
                typePriceList[instanceType] = [[region[1], priceTotal[0][0], priceTotal[0][1]]]
            # print(typePriceList)
            # exit()
        # print(typePriceList)
        # exit()

        # option = []
        for instance, typeItem in typePriceList.items():
            print(instance)
            for zoneItem in typeItem:
                print(zoneItem)
                # option.append([instance, zoneItem[0], zoneItem[1]])
            print()

        # end = time.time()
        # print(end-start, 's')
        # print()

        instanceType = selectOption('重新选择规格No：', option, False)
        print(instanceType)
        print()

elif action == 2:
    
    # 选择地域
    RegionId = selectOption('选择地域：', regionList)
    client = AcsClient(AccessKeyID, AccessKeySecret, RegionId)
    print()

    # 查看实例
    request = DescribeInstancesRequest()
    request.set_accept_format('json')
    response = client.do_action_with_exception(request)
    response = json.loads(response)
    print(json.dumps(response, indent=2))

elif action == 1:
    
    # 选择地域
    RegionId = selectOption('选择地域：', regionList)
    client = AcsClient(AccessKeyID, AccessKeySecret, RegionId)
    print()

    # 查看规格 DescribeInstanceTypes

    typeAction = selectOption('选择操作：', [
        ['查找规格'],
        ['指定规格'],
        ['预设规格'],
    ])

    option = []

    if typeAction == 0:
        cpu = input('CPU核素：')
        memory = input('内存大小(G)：')
        gpu = input('GPU核素：')
        if cpu == '':
            cpu = 0
        if memory == '':
            memory = 0
        if gpu == '':
            gpu = 0
        cpu = int(cpu)
        memory = int(memory)
        gpu = int(gpu)

        print("No\tCPU\tMemory\tGPU\tBandwidth\tPps\tInstanceTypeId")
        # for i in typeList:
        # 查看InstanceTypeFamily下的规格
        request = DescribeInstanceTypesRequest()
        request.set_accept_format('json')
        # request.set_InstanceTypeFamily('ecs.' + i)

        response = client.do_action_with_exception(request)
        response = json.loads(response)
        # print(json.dumps(response,indent=2))
        for item in response['InstanceTypes']['InstanceType']:
            if cpu!=0 and item['CpuCoreCount'] != cpu:
                continue
            if memory!=0 and item['MemorySize'] != memory:
                continue
            if gpu!=0 and item['GPUAmount'] != gpu:
                continue
            if 'InstanceBandwidthRx' not in item:
                item['InstanceBandwidthRx'] = 0
            if 'InstancePpsRx' not in item:
                item['InstancePpsRx'] = 0
            option.append([
                "\t" + 
                str(item['CpuCoreCount']) + "\t" + 
                str(int(item['MemorySize'])) + "\t" + 
                str(item['GPUAmount']) + "\t" + 
                str(item['InstanceBandwidthRx']/1024000)+'k' + "\t\t" + 
                str(int(item['InstancePpsRx']/10000))+'W' + "\t" +
                str(item['InstanceTypeId']), 
                str(item['InstanceTypeId'])
            ])
        # exit()
        # InstanceType = input('输入规格InstanceType：')
        InstanceType = selectOption('选择规格No：', option)

    elif typeAction == 1:
        InstanceType = input('输入规格InstanceType：')

    elif typeAction == 2:

        print("No\tCPU\tMemory\tGPU\tBandwidth\tPps\tInstanceTypeId")
        for i in typeList:
            # 查看InstanceTypeFamily下的规格
            request = DescribeInstanceTypesRequest()
            request.set_accept_format('json')
            request.set_InstanceTypeFamily('ecs.' + i)

            response = client.do_action_with_exception(request)
            response = json.loads(response)
            # print(json.dumps(response,indent=2))
            for item in response['InstanceTypes']['InstanceType']:
                if 'InstanceBandwidthRx' not in item:
                    item['InstanceBandwidthRx'] = 0
                if 'InstancePpsRx' not in item:
                    item['InstancePpsRx'] = 0
                option.append([
                    "\t" + 
                    str(item['CpuCoreCount']) + "\t" + 
                    str(int(item['MemorySize'])) + "\t" + 
                    str(item['GPUAmount']) + "\t" + 
                    str(item['InstanceBandwidthRx']/1024000)+'k' + "\t\t" + 
                    str(int(item['InstancePpsRx']/10000))+'W' + "\t" +
                    str(item['InstanceTypeId']), 
                    str(item['InstanceTypeId'])
                ])
        # exit()
        # InstanceType = input('输入规格InstanceType：')
        InstanceType = selectOption('选择规格No：', option)

    print(InstanceType)
    print()

    # 查看抢占式实例近30日价格

    request = DescribeSpotPriceHistoryRequest()
    request.set_accept_format('json')

    request.set_NetworkType("vpc")
    request.set_InstanceType(InstanceType)
    day30 = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    request.set_StartTime(day30)

    response = client.do_action_with_exception(request)
    # print(json.dumps(json.loads(response),indent=2))
    response = json.loads(response)
    price = {}
    for i in response['SpotPrices']['SpotPriceType']:
        if i['ZoneId'] in price:
            price[i['ZoneId']].append(i['SpotPrice'])
        else:
            price[i['ZoneId']] = [i['SpotPrice']]
    
    if price == {}:
        print('没有可用区有卖该机型')
        exit()

    num = selectOption('是否对比价格：', [
        ["是"], ["否"]
    ])
    if num == 0:
        # 图表
        for i in price:
            plt.plot(price[i], label=i)
            plt.text(len(price[i])-1, price[i][len(price[i])-1], price[i][len(price[i])-1])
        plt.legend()
        plt.title("price")
        plt.show()
    print()

    option = []
    for zoneId in price:
        option.append([zoneId, zoneId])
    ZoneId = selectOption('选择可用区：', option)
    print(ZoneId)
    print()


    # 查询镜像
    ImageOwnerAlias = selectOption('选择镜像：', [
        ['系统', 'system'],
        ['自有', 'self'],
    ])
    # print(ImageOwnerAlias)
    print(ImageOwnerAlias)
    print()

    request = DescribeImagesRequest()
    request.set_accept_format('json')
    # 镜像类型
    # system：阿里云提供的公共镜像。
    # self：您创建的自定义镜像。
    # others：其他阿里云用户共享给您的镜像。
    # marketplace：镜像市场提供的镜像。您查询到的云市场镜像可以直接使用，无需提前订阅。您需要自行留意云市场镜像的收费详情。
    # request.set_ImageOwnerAlias("system")
    request.set_ImageOwnerAlias(ImageOwnerAlias)
    request.set_OSType("linux")

    response = client.do_action_with_exception(request)
    response = json.loads(response)
    if ImageOwnerAlias == "system":
        # print("No\t%-50s" % "ImageId", "System")
        # for item in response['Images']['Image']:
        #     print("%-50s" % item['ImageId'], item['OSNameEn'])
        option = []
        print("No\t%-50s" % "ImageId", "System")
        for item in response['Images']['Image']:
            option.append([item['ImageId'] + "\t" + item['OSNameEn'] , item['ImageId']])
        ImageId = selectOption('选择镜像：', option)
        # ImageId = input('输入镜像ImageId：')
    else:
        print(json.dumps(response, indent=2))
        ImageId = input('输入镜像ImageId：')
    print(ImageId)
    print()


    # 查看网络安全组
    request = DescribeSecurityGroupsRequest()
    request.set_accept_format('json')
    request.set_NetworkType('vpc') # vpc 专有网络 classic 经典网络
    response = client.do_action_with_exception(request)
    response = json.loads(response)
    # print(json.dumps(response, indent=2))
    
    option = []
    print("%-3s %-25s %-25s %-10s %s" % ("No", "SecurityGroupName", "SecurityGroupId", "Type", "Description"))
    for group in response['SecurityGroups']['SecurityGroup']:
        option.append([("{:<25} {:<25} {:<10} {}".format(group['SecurityGroupName'], group['SecurityGroupId'], group['SecurityGroupType'], group['Description'])) , group['SecurityGroupId']])
    SecurityGroupId = selectOption('选择网络安全组：', option)
    # SecurityGroupId = input('输入网络安全组SecurityGroupId：')
    print(SecurityGroupId)
    print()

    # SecurityGroupId = 'sg-wz91p7ptv6xmli1thxx5' # normal
    # SecurityGroupId = 'sg-j6c83nnofp3l7cjwwlg7' # open

    # 查看专有网络VPC 交换机
    # https://help.aliyun.com/document_detail/35748.html

    request = DescribeVSwitchesRequest()
    request.set_accept_format('json')
    # request.set_ZoneId(ZoneId)

    response = client.do_action_with_exception(request)
    response = json.loads(response)
    # print(json.dumps(response, indent=2))
    # exit()

    option = []
    print("%-3s %-25s %-10s %s" % ("No", "VSwitchId", "Name", "Description"))
    for group in response['VSwitches']['VSwitch']:
        if group['ZoneId'] == ZoneId:
            option.append(["{:<25} {:<10} {}".format(group['VSwitchId'], group['VSwitchName'], group['Description']) , group['VSwitchId']])
    VSwitchId = selectOption('选择专有网络VPC交换机：', option)
    # VSwitchId = input('输入专有网络VPC交换机VSwitchId：')
    print(VSwitchId)
    print()


    # 创建实例
    # https://help.aliyun.com/document_detail/63440.html

    request = RunInstancesRequest()
    request.set_accept_format('json')

    # request.set_DryRun(self.dry_run)
    request.set_InstanceType(InstanceType)
    # InternetChargeType 网络计费类型
    # PayByBandwidth 固定流量  PayByTraffic 按流量计费
    request.set_InternetChargeType("PayByTraffic")
    request.set_ImageId(ImageId)
    # SecurityGroupId 决定了实例的网络类型 
    # 如果指定安全组的网络类型为专有网络VPC，实例则为VPC类型，并同时需要指定参数VSwitchId。
    request.set_SecurityGroupId(SecurityGroupId)
    # request.set_Period(self.period)
    # request.set_PeriodUnit(self.period_unit)
    request.set_ZoneId(ZoneId)
    # InstanceChargeType 实例的付费方式
    # PrePaid：包年包月。
    # PostPaid（默认）：按量付费。
    request.set_InstanceChargeType("PostPaid")
    request.set_InstanceName("test")
    request.set_Password("Test123!")
    # request.set_Amount(self.amount)
    request.set_InternetMaxBandwidthOut(1) # 出网带宽
    # request.set_IoOptimized(self.io_optimized)
    # SpotStrateg 按量实例的抢占策略
    # 当InternetChargeType是PostPaid时有效
    # NoSpot（默认）：正常按量付费实例。
    # SpotWithPriceLimit：设置上限价格的抢占式实例。
    # SpotAsPriceGo：系统自动出价，跟随当前市场实际价格。
    request.set_SpotStrategy("SpotAsPriceGo")
    # 竞价价格上限
    # request.set_SpotPriceLimit(self.spot_price_limit)
    # request.set_SecurityEnhancementStrategy(self.security_enhancement_strategy)
    # 硬盘，最少20
    request.set_SystemDiskSize("40")
    # 系统盘的磁盘种类
    # request.set_SystemDiskCategory(self.system_disk_category)
    
    # request.set_AutoReleaseTime("2019-12-12T00:00:00Z") # 自动释放时间
    request.set_VSwitchId(VSwitchId) #vsw-bp1kk71yrvrwvpior0els

    response = client.do_action_with_exception(request)
    response = json.loads(response)
    print(json.dumps(response, indent=2))


    # 查看实例详情
    # if 'InstanceIdSets' in response and 'InstanceIdSet' in response['InstanceIdSets']:
    #     request = DescribeInstancesRequest()
    #     request.set_accept_format('json')
    #     request.set_InstanceIds([response['InstanceIdSets']['InstanceIdSet'][0]]) # 可选
    #     response = client.do_action_with_exception(request)
    #     response = json.loads(response)
    #     print(json.dumps(response, indent=2))

elif action == 3:

    # 选择地域
    RegionId = selectOption('选择地域：', regionList)
    client = AcsClient(AccessKeyID, AccessKeySecret, RegionId)
    print()

    InstanceId = input('输入实例 InstanceId：')

    # 释放实例

    request = DeleteInstanceRequest()
    request.set_accept_format('json')

    request.set_InstanceId(InstanceId)
    request.set_Force(True)

    response = client.do_action_with_exception(request)
    print(json.dumps(json.loads(response),indent=2))

# 没有设置虚拟交换机ID：
# aliyunsdkcore.acs_exception.exceptions.ServerException: HTTP Status: 403 Error:OperationDenied.InvalidNetworkType The specified network type is not available in the specified region.
# 获取院内网患者列表json转换为列表，新增 床位+住院号+姓名+诊断 字典项

# %%

import requests
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

# %%

# 而在requests库中，不用json.loads方法进行反序列化
# 而是提供了响应对象的json方法，用来对json格式的响应体进行反序列化，获得list
hpListRaw = requests.get(
    'http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30046/33A/A002', headers=headers).json()

hpList = [{key: d[key] for key in ['bedid', 'pname', 'mrn', 'diag']}
          for d in hpListRaw]

# hpList的每个字典新建一项pinfo,内容由 bedid,pname,mrn 合并产生，中间由“-”分隔
for item in hpList:
    item['pinfo'] = str(item['bedid'])+'-'+item['pname'] + \
        '-'+str(item['mrn'])+'-'+item['diag']


# %%
# 获取trello列表

tBoardId = "65296c002df7c2c909517c4e"

url = f"https://api.trello.com/1/boards/{tBoardId}/lists"

headers = {
    "Accept": "application/json"
}

query = {
    'key': 'f45b896485c79fe922e7f022a8bc6f71',
    'token': 'ATTAae59e22e7d144839c54a444aa4f24d4f3ede09405b11ace472e773a78a23b0e8F2D629A2'
}

response = requests.request(
    "GET",
    url,
    headers=headers,
    params=query,
    verify = False
)

# 从response.json()获得的list中保留id,name,并排除name为"test"的项目,将剩余的项目的name值按"-"分解并获取第三项,保留为键值"mrn"

pattern = r'^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-.*$'

tpList = [{key: d[key] for key in ['id', 'name']}
          for d in response.json() if re.match(pattern, d['name'])]
for item in tpList:
    item['mrn'] = int(item['name'].split('-')[2])

# 根据mrn同步tpList和hpList
# 如果hpList中有tpList中没有的,则增加一项,将hplist的pinfo项赋值给tplist的name项,如果tpList中有hpList中没有的,则删除这一项
# 将hpList中的每一项的mrn与tpList中的每一项的mrn进行比较，如果相等，则将hpList中的该项的pinfo赋值给tpList中的该项的name

# GitHub Copilot: `if not any()`是Python中的一个条件语句，用于检查一个可迭代对象中是否存在任何一个元素满足某个条件。如果没有任何元素满足条件，则返回`True`，否则返回`False`。
# 在这个代码块中，`if not any(d['mrn'] == item['mrn'] for d in hpList)`的意思是：如果在`hpList`中没有任何一个元素的`mrn`属性与当前的`item`元素的`mrn`属性相等，则执行下面的代码块。如果存在一个或多个元素的`mrn`属性与当前的`item`元素的`mrn`属性相等，则不执行下面的代码块。
# 换句话说，这个条件语句用于检查`hpList`中是否存在一个与当前`item`元素具有相同`mrn`属性的元素。如果不存在，则执行下面的代码块，否则不执行。

# %% 

for item in hpList:
    if not any(d['mrn'] == item['mrn'] for d in tpList):
        requests.request(
            "POST",
            f"https://api.trello.com/1/boards/{tBoardId}/lists",
            headers=headers,
            params=dict({"name":item['pinfo']},**query),
            verify = False,
        )
        print("add "+item['pinfo'])
    else:
        for d in tpList:
            if d['mrn'] == item['mrn'] and d['name'] != item['pinfo']:
                requests.request(
                    "PUT",
                    f"https://api.trello.com/1/lists/{d['id']}",
                    params=dict({"name":item['pinfo']},**query),
                    verify = False,
                )
                print("rename " + item['pinfo'])
for item in tpList:
    if not any(d['mrn'] == item['mrn'] for d in hpList):
        requests.request(
            "PUT",
            f"https://api.trello.com/1/lists/{item['id']}/closed",
            params=dict({'value':"true"},**query),
            verify = False,
        )
        print("del " + item['name'])
# %%

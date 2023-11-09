# %%
import requests
import re
import json
import base64
import pandas as pd
import datetime

# 导入 functions.py
from functions import *

# %%
# trello

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

query = {
    'key': 'f45b896485c79fe922e7f022a8bc6f71',
    'token': 'ATTAae59e22e7d144839c54a444aa4f24d4f3ede09405b11ace472e773a78a23b0e8F2D629A2',
}

headers = {
    "Accept": "application/json"
}

# %%
# trello上获取患者住院号列表和id列表，并排除其他无关列表

tpListRaw = requests.request(
    "GET",
    "https://api.trello.com/1/boards/65296c002df7c2c909517c4e/lists",
    headers=headers,
    params=query,
    verify = False,
).json()

pattern = r'^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-[\u4e00-\u9fa5]*$'

tpList = [{key: d[key] for key in ['id', 'name']}
          for d in tpListRaw if re.match(pattern, d['name'])]
for item in tpList:
    item['mrn'] = int(item['name'].split('-')[2])

# %%  住院系统获取患者列表 

# 获取患者列表，得到住院号mrn和series
# http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30046/33A/A002

hpListRaw = requests.get(
    'http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30046/33A/A002', headers=headers).json()

hpList = [{key: d[key] for key in ['bedid', 'pname', 'mrn', 'series', 'diag', 'admdays']}
          for d in hpListRaw]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

# %% 
#  根据mrn列合并hpList和tplist，保存到pList，要求保存hpList中的所有行，tplist中的id列
pList = pd.merge(pd.DataFrame(hpList), pd.DataFrame(tpList), on='mrn', how='left')


# %% 遍历plist, 获取患者信息

pContent = ""

pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>每日更新</h1>\n<!-- /wp:heading -->\n"

for index, row in pList.iterrows():
    # 获取病历文书列表
    # http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/{mrn}/{series}/emr
    # 筛选出
    # "docname": "麻醉前访视单"
    
    print(row['mrn'])

    if int(row['admdays']) > 2:
        duration = 1
    else:
        duration = 30

    hDocuList = requests.get(f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/{row['mrn']}/{row['series']}/emr", headers=headers).json()
        
    pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>{row['name']}</h2>\n<!-- /wp:heading -->\n"

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>化验结果</h3>\n<!-- /wp:heading -->\n"
    pContent += get_lab_results(row['mrn'], duration)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>检查结果</h3>\n<!-- /wp:heading -->\n"
    pContent += get_exam_results(row['mrn'], duration)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>会诊结果</h3>\n<!-- /wp:heading -->\n"
    pContent += consultation(hDocuList)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>既往史</h3>\n<!-- /wp:heading -->\n"

    pContent += "<!-- wp:heading {'level':4} -->\n<h4 class='wp-block-heading'>麻醉会诊</h4>\n<!-- /wp:heading -->\n"
    pContent += get_preAnesth(hDocuList)

    pContent += "<!-- wp:heading {'level':4} -->\n<h4 class='wp-block-heading'>护理记录</h4>\n<!-- /wp:heading -->\n"
    pContent += get_nurse_doc(row['mrn'],row['series'])

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>医嘱</h3>\n<!-- /wp:heading -->\n"
    pContent += get_order(row['mrn'],row['series'])

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>手术记录</h3>\n<!-- /wp:heading -->\n"
    pContent += surgicalRecord(hDocuList)

pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>手术安排</h1>\n<!-- /wp:heading -->\n"

surgical_arrange_df = surgical_arrange_check()

pContent += surgical_arrange_df.to_html()
# %%

# 筛选出rj_df里 Isroom为“日间“的列
rj_df = surgical_arrange_df[surgical_arrange_df['Isroom'] == '日间'].copy()
# 新建 pBrief 列，格式为 PatientName+mrn+Diagnose 
rj_df.loc[:,'pBrief'] = rj_df['PatientName'].str.cat(rj_df[['mrn', 'Diagnose']].astype(str), sep='+')

pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>日间手术</h1>\n<!-- /wp:heading -->\n"

for index, row in rj_df.iterrows():
    
    pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>{row['pBrief']}</h2>\n<!-- /wp:heading -->\n"

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>化验结果</h3>\n<!-- /wp:heading -->\n"
    pContent += get_lab_results(row['mrn'], 30)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>检查结果</h3>\n<!-- /wp:heading -->\n"
    pContent += get_exam_results(row['mrn'], 30)

# %%
# https://robingeuens.com/blog/python-wordpress-api/

user = "zhihuai1982"
password = "UA5v egrD T2El 9htA c16a SwDA"
credentials = user + ':' + password
token = base64.b64encode(credentials.encode())
header = {'Authorization': 'Basic ' + token.decode('utf-8')}

# 读取 response.json， 如果 modified 提供的日期和今天的日期相同，则把 id 信息保存到变量 todayPostID 里

# Load the data from the JSON file
with open('response.json', 'r') as f:
    jsondata = json.load(f)

# Get today's date as a string
today = datetime.datetime.now().strftime('%Y-%m-%d')

# Check if the 'modified' date in the data is today
if jsondata.get('modified').split('T')[0] == today:
    # If so, save the 'id' to the variable todayPostID
    todayPostID = jsondata.get('id')
else:
    todayPostID = '' 

url = f"https://www.digitalnomad.host:8766/wp-json/wp/v2/posts/{todayPostID}"
post = {
'title' : f"患者病情简报 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
'status' : 'publish',
'content' : pContent
}
response = requests.post(url , headers=header, json=post, verify = False)
print(response)

# %%

# Parse the response text as JSON
response_data = json.loads(response.text)

# Extract the id and date
data_to_save = {
    'id': response_data.get('id'),
    'date': response_data.get('date'),
    'modified': response_data.get('modified')
}

# Save the data to a JSON file
with open('response.json', 'w') as f:
    json.dump(data_to_save, f)
# %%

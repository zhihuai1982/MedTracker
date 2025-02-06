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

trelloheaders = {
    "Accept": "application/json"
}

# %%
# trello上获取患者住院号列表和id列表，并排除其他无关列表

tpListRaw = requests.request(
    "GET",
    "https://api.trello.com/1/boards/677a48e65ad0abf1e767ab41/lists",
    headers=trelloheaders,
    params=query,
    verify=False,
).json()

pattern = r'^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-.*$'

tpList = [{key: d[key] for key in ['id', 'name']}
          for d in tpListRaw if re.match(pattern, d['name'])]
for item in tpList:
    item['mrn'] = int(item['name'].split('-')[2])
    item['tdiag'] = item['name'].split('-')[3]

# %%  住院系统获取患者列表

# 获取患者列表，得到住院号mrn和series
# http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30046/33A/A002

hpListRaw = requests.get(
    'http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30259/33/A001', headers=headers).json()

hpList = [{key: d[key] for key in ['bedid', 'pname', 'mrn', 'series', 'diag', 'admdays']}
          for d in hpListRaw]

# # hpList 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天
# for item in hpList:
#     item['h2name'] = f"{item['bedid']}-{item['pname']
#                                         }-{item['mrn']}-{item['admdays']}d-{item['diag']}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

# %%
#  根据mrn列合并hpList和tplist，保存到pList，要求保存hpList中的所有行，tplist中的id列
pList = pd.merge(pd.DataFrame(hpList), pd.DataFrame(
    tpList), on='mrn', how='left')

# 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天-tdiag
pList['h2name'] = pList['bedid'].astype(str)+'-'+pList['pname']+'-'+pList['admdays'].astype(str)+'d-'+pList['tdiag'] + "-" + pList['mrn'].astype(
    str)

# pList 根据  bedid 列逆序排列
pList = pList.sort_values(by='bedid', ascending=False)

# pList = pList.iloc[:1]

# %%

pContent = ""

# pContent += "<!-- wp:heading {'level':1} -->\n<div id='xiao-notes'><h1 class='wp-block-heading'>肖组备注</h1></div>\n<!-- /wp:heading -->\n"

for index, row in pList.iterrows():

    # print(row['mrn'])
    pContent += f"<!-- wp:heading -->\n<h4 class='wp-block-heading'><a class='note_link' href='#{row['h2name']}'>{
        row['h2name']}</a></h4>\n<!-- /wp:heading -->\n"
    # pContent += trello_note(row['id'], "together", notify="true")
    pContent += trello_note(row['id'], "together")


# %%
# https://robingeuens.com/blog/python-wordpress-api/

user = "zhihuai1982"
# password = "BSNz VB3W InRj LlFr ueKU 1ZSk"
password = "dtPD 9emY eyH8 Vcbn nl31 WKMr"
credentials = user + ':' + password
token = base64.b64encode(credentials.encode())
header = {'Authorization': 'Basic ' + token.decode('utf-8')}

# 读取 response.json， 如果 modified 提供的日期和今天的日期相同，则把 id 信息保存到变量 todayPostID 里

# Load the data from the JSON file
with open('response_notify.json', 'r') as f:
    jsondata = json.load(f)

# Get today's date as a string
today = datetime.datetime.now().strftime('%Y-%m-%d')

# Check if the 'modified' date in the data is today
if jsondata.get('modified').split('T')[0] == today:
    # If so, save the 'id' to the variable todayPostID
    todayPostID = jsondata.get('id')
else:
    todayPostID = ''

# todayPostID = ''
url = f"https://www.digitalnomad.host:996/wp-json/wp/v2/posts/{todayPostID}"
post = {
    'title': f"今日简报 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    'status': 'publish',
    'content': pContent
}
response_notify = requests.post(url, headers=header, json=post, verify=False)
print(response_notify)

# %%

# Parse the response text as JSON
response_data = json.loads(response_notify.text)

# Extract the id and date
data_to_save = {
    'id': response_data.get('id'),
    'date': response_data.get('date'),
    'modified': response_data.get('modified')
}

# Save the data to a JSON file
with open('response_notify.json', 'w') as f:
    json.dump(data_to_save, f)
# %%

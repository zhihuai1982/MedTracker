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
    "https://api.trello.com/1/boards/656726edf8be9744bc4009a4/lists",
    headers=trelloheaders,
    params=query,
    verify=False,
).json()

pattern = r'^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-.*$'

tpList = [{key: d[key] for key in ['id', 'name']}
          for d in tpListRaw if re.match(pattern, d['name'])]
for item in tpList:
    item['mrn'] = int(item['name'].split('-')[2])

# %%  住院系统获取患者列表

# 获取患者列表，得到住院号mrn和series
# http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30043/33/A001

hpListRaw = requests.get(
    'http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30043/33/A001', headers=headers).json()

hpList = [{key: d[key] for key in ['bedid', 'pname', 'mrn', 'series', 'diag', 'admdays']}
          for d in hpListRaw]

# hpList 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天
for item in hpList:
    item['h2name'] = f"{item['bedid']}-{item['pname']
                                        }-{item['mrn']}-{item['admdays']}d-{item['diag']}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

# %%
#  根据mrn列合并hpList和tplist，保存到pList，要求保存hpList中的所有行，tplist中的id列
pList = pd.merge(pd.DataFrame(hpList), pd.DataFrame(
    tpList), on='mrn', how='left')

# pList 根据  bedid 列逆序排列
pList = pList.sort_values(by='bedid', ascending=False)


# %%

pContent = ""

pContent += "<!-- wp:heading {'level':1} -->\n<div id='hou-notes'><h1 class='wp-block-heading'>侯组备注</h1></div>\n<!-- /wp:heading -->\n"

for index, row in pList.iterrows():

    print(row['mrn'])
    pContent += f"<!-- wp:heading -->\n<h4 class='wp-block-heading'><a class='note_link' href='#{row['h2name'].replace("(", "").replace(")", "")}'>{
        row['h2name']}</a></h4>\n<!-- /wp:heading -->\n"
    pContent += trello_note(row['id'], "together")

pContent += "<!-- wp:heading -->\n<h4 class='wp-block-heading'>其他备注</h4>\n<!-- /wp:heading -->\n"
pContent += trello_note("65672a615c743386d9043191", "other")
pContent += f"<!-- wp:shortcode --> [note_form idlist='65672a615c743386d9043191'] <!-- /wp:shortcode -->\n"

# %% 遍历plist, 获取患者信息

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

    hDocuList = requests.get(
        f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/{row['mrn']}/{row['series']}/emr", headers=headers).json()

    pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>{
        row['h2name']}</h2>\n<!-- /wp:heading -->\n"

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#hou-notes'>备注</a></h3>\n<!-- /wp:heading -->\n"

    pContent += "<ul style='font-size:40px;'>" + \
        trello_note(row['id'], "scatter") + "</ul>\n"

    pContent += f"<!-- wp:shortcode --> [note_form idlist='{
        row['id']}'] <!-- /wp:shortcode -->\n"

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#hou-notes'>生命体征</a></h3>\n<!-- /wp:heading -->\n"
    pContent += highcharts(row['mrn'], row['series'])

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#hou-notes'>化验结果</a></h3>\n<!-- /wp:heading -->\n"
    pContent += "<div class='table_container'>" + \
        get_lab_results(row['mrn'], duration) + "</div>\n"

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#hou-notes'>检查结果</a></h3>\n<!-- /wp:heading -->\n"
    pContent += get_exam_results(row['mrn'], duration)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#hou-notes'>会诊结果</a></h3>\n<!-- /wp:heading -->\n"
    pContent += consultation(hDocuList)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#hou-notes'>既往史</a></h3>\n<!-- /wp:heading -->\n"

    pContent += "<!-- wp:heading {'level':4} -->\n<h4 class='wp-block-heading'><a class='note_link' href='#hou-notes'>麻醉会诊</a></h4>\n<!-- /wp:heading -->\n"
    pContent += get_preAnesth(hDocuList)

    pContent += "<!-- wp:heading {'level':4} -->\n<h4 class='wp-block-heading'><a class='note_link' href='#hou-notes'>护理记录</a></h4>\n<!-- /wp:heading -->\n"
    pContent += get_nurse_doc(row['mrn'], row['series'])

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#hou-notes'>医嘱</a></h3>\n<!-- /wp:heading -->\n"
    pContent += get_order(row['mrn'], row['series'], row['id'], query)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#hou-notes'>首次病程录</a></h3>\n<!-- /wp:heading -->\n"
    pContent += medicalHistory(hDocuList)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#hou-notes'>手术记录</a></h3>\n<!-- /wp:heading -->\n"
    pContent += surgicalRecord(hDocuList)


surgical_check_df, inpatient_check_df, surgical_arrange_df, fromDay_str, toDay_str, nextFromDay_str, nextToDay_str = surgical_arrange_check(
    pList, "30043", "侯铁宁")

pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>手术安排</h1>\n<!-- /wp:heading -->\n"

pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>预约患者手术安排 {
    fromDay_str}_{toDay_str}</h2>\n<!-- /wp:heading -->\n"

# 如果 surgical_check_df 有 11 列
if surgical_check_df.shape[1] == 11:
    surgicalStyles = [
        {'selector': 'th.col_heading.level0.col0',
            'props': [('width', '40px')]},
        {'selector': 'th.col_heading.level0.col1',
            'props': [('width', '40px')]},
        {'selector': 'th.col_heading.level0.col2',
            'props': [('width', '80px')]},
        {'selector': 'th.col_heading.level0.col3',
            'props': [('width', '80px')]},
        {'selector': 'th.col_heading.level0.col4',
            'props': [('width', '40px')]},
        {'selector': 'th.col_heading.level0.col5',
            'props': [('width', '40px')]},
        {'selector': 'th.col_heading.level0.col6',
            'props': [('width', '60px')]},
        {'selector': 'th.col_heading.level0.col7',
            'props': [('width', '100px')]},
        {'selector': 'th.col_heading.level0.col8',
            'props': [('width', '100px')]},
        {'selector': 'th.col_heading.level0.col9',
            'props': [('width', '180px')]},
        {'selector': 'th.col_heading.level0.col10',
            'props': [('width', '100px')]}
    ]
    pContent += "<div class='table-container'> " + \
        surgical_check_df.style.hide().set_table_styles(
            surgicalStyles).to_html() + "</div>\n"
else:
    pContent += "<div class='table-container'> " + \
        surgical_check_df.to_html(index=False) + "</div>\n"

pContent += "<!-- wp:heading -->\n<h2 class='wp-block-heading'>在院患者手术安排</h2>\n<!-- /wp:heading -->\n"

pContent += "<div class='table-container'> " + \
    inpatient_check_df.to_html(index=False) + "</div>\n"

pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>NEXT患者 {
    nextFromDay_str}_{nextToDay_str}</h2>\n<!-- /wp:heading -->\n"

pContent += "<div class='table-container'> " + \
    surgical_arrange_df.to_html(index=False) + "</div>\n"


# %%

# 筛选出rj_df里 Isroom为“日间“的列
rj_df = surgical_check_df[surgical_check_df['Isroom'] == '日间'].copy()

# rj_df 删除mrn列与pList的mrn相同的行
rj_df = rj_df[~rj_df['mrn'].isin(pList['mrn'])]

# 如果rj_df不为空
if not rj_df.empty:
    # 新建 pBrief 列，格式为 PatientName+mrn+Diagnose
    rj_df.loc[:, 'pBrief'] = rj_df['PatientName'].str.cat(
        rj_df[['mrn', 'Diagnose']].astype(str), sep='+')

    pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>日间手术</h1>\n<!-- /wp:heading -->\n"

    for index, row in rj_df.iterrows():

        pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>{
            row['pBrief']}</h2>\n<!-- /wp:heading -->\n"

        pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>化验结果</h3>\n<!-- /wp:heading -->\n"
        pContent += get_lab_results(row['mrn'], 30)

        pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'>检查结果</h3>\n<!-- /wp:heading -->\n"
        pContent += get_exam_results(row['mrn'], 30)


# %%
# trello上获取患者住院号列表和id列表，并排除其他无关列表

tpListRaw = requests.request(
    "GET",
    "https://api.trello.com/1/boards/655c91ee0b0743282fcd85fe/lists",
    headers=trelloheaders,
    params=query,
    verify=False,
).json()

pattern = r'^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-.*$'

tpList = [{key: d[key] for key in ['id', 'name']}
          for d in tpListRaw if re.match(pattern, d['name'])]
for item in tpList:
    item['mrn'] = int(item['name'].split('-')[2])

# %%  住院系统获取患者列表

# 获取患者列表，得到住院号mrn和series
# http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30046/33A/A002

hpListRaw = requests.get(
    'http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30259/33/A001', headers=headers).json()

hpList = [{key: d[key] for key in ['bedid', 'pname', 'mrn', 'series', 'diag', 'admdays']}
          for d in hpListRaw]

# hpList 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天
for item in hpList:
    item['h2name'] = f"{item['bedid']}-{item['pname']
                                        }-{item['mrn']}-{item['admdays']}d-{item['diag']}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

# %%
#  根据mrn列合并hpList和tplist，保存到pList，要求保存hpList中的所有行，tplist中的id列
pList = pd.merge(pd.DataFrame(hpList), pd.DataFrame(
    tpList), on='mrn', how='left')

# 删除pList中mrn列为“9454931”的行
pList = pList[pList['mrn'] != 9454931]

# pList 根据  bedid 列逆序排列
pList = pList.sort_values(by='bedid', ascending=False)

# %%

# pContent = ""

pContent += "<!-- wp:heading {'level':1} -->\n<div id='xiao-notes'><h1 class='wp-block-heading'>肖组备注</h1></div>\n<!-- /wp:heading -->\n"

for index, row in pList.iterrows():

    print(row['mrn'])
    pContent += f"<!-- wp:heading -->\n<h4 class='wp-block-heading'><a class='note_link' href='#{row['h2name'].replace("(", "").replace(")", "")}'>{
        row['h2name']}</a></h4>\n<!-- /wp:heading -->\n"
    pContent += trello_note(row['id'], "together")

pContent += "<!-- wp:heading -->\n<h4 class='wp-block-heading'>其他备注</h4>\n<!-- /wp:heading -->\n"
pContent += trello_note("655c9b555dc15db6beb5da79", "other")
pContent += f"<!-- wp:shortcode --> [note_form idlist='655c9b555dc15db6beb5da79'] <!-- /wp:shortcode -->\n"

# %% 遍历plist, 获取患者信息

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

    hDocuList = requests.get(
        f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/{row['mrn']}/{row['series']}/emr", headers=headers).json()

    pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>{
        row['h2name']}</h2>\n<!-- /wp:heading -->\n"

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>备注</a></h3>\n<!-- /wp:heading -->\n"

    pContent += "<ul style='font-size:40px;'>" + \
        trello_note(row['id'], "scatter") + "</ul>\n"

    pContent += f"<!-- wp:shortcode --> [note_form idlist='{
        row['id']}'] <!-- /wp:shortcode -->\n"

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>生命体征</a></h3>\n<!-- /wp:heading -->\n"
    pContent += highcharts(row['mrn'], row['series'])

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>化验结果</a></h3>\n<!-- /wp:heading -->\n"
    pContent += "<div class='table_container'>" + \
        get_lab_results(row['mrn'], duration) + "</div>\n"

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>检查结果</a></h3>\n<!-- /wp:heading -->\n"
    pContent += get_exam_results(row['mrn'], duration)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>会诊结果</a></h3>\n<!-- /wp:heading -->\n"
    pContent += consultation(hDocuList)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>既往史</a></h3>\n<!-- /wp:heading -->\n"

    pContent += "<!-- wp:heading {'level':4} -->\n<h4 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>麻醉会诊</a></h4>\n<!-- /wp:heading -->\n"
    pContent += get_preAnesth(hDocuList)

    pContent += "<!-- wp:heading {'level':4} -->\n<h4 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>护理记录</a></h4>\n<!-- /wp:heading -->\n"
    pContent += get_nurse_doc(row['mrn'], row['series'])

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>医嘱</a></h3>\n<!-- /wp:heading -->\n"
    pContent += get_order(row['mrn'], row['series'], row['id'], query)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>首次病程录</a></h3>\n<!-- /wp:heading -->\n"
    pContent += medicalHistory(hDocuList)

    pContent += "<!-- wp:heading {'level':3} -->\n<h3 class='wp-block-heading'><a class='note_link' href='#xiao-notes'>手术记录</a></h3>\n<!-- /wp:heading -->\n"
    pContent += surgicalRecord(hDocuList)

surgical_check_df, inpatient_check_df, surgical_arrange_df, fromDay_str, toDay_str, nextFromDay_str, nextToDay_str = surgical_arrange_check(
    pList, "30259", "肖芒")

pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>手术安排</h1>\n<!-- /wp:heading -->\n"

pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>预约患者手术安排 {
    fromDay_str}_{toDay_str}</h2>\n<!-- /wp:heading -->\n"

# 如果 surgical_check_df 有 11 列
if surgical_check_df.shape[1] == 11:
    surgicalStyles = [
        {'selector': 'th.col_heading.level0.col0',
            'props': [('width', '40px')]},
        {'selector': 'th.col_heading.level0.col1',
            'props': [('width', '40px')]},
        {'selector': 'th.col_heading.level0.col2',
            'props': [('width', '80px')]},
        {'selector': 'th.col_heading.level0.col3',
            'props': [('width', '80px')]},
        {'selector': 'th.col_heading.level0.col4',
            'props': [('width', '40px')]},
        {'selector': 'th.col_heading.level0.col5',
            'props': [('width', '40px')]},
        {'selector': 'th.col_heading.level0.col6',
            'props': [('width', '60px')]},
        {'selector': 'th.col_heading.level0.col7',
            'props': [('width', '100px')]},
        {'selector': 'th.col_heading.level0.col8',
            'props': [('width', '100px')]},
        {'selector': 'th.col_heading.level0.col9',
            'props': [('width', '180px')]},
        {'selector': 'th.col_heading.level0.col10',
            'props': [('width', '100px')]}
    ]
    pContent += "<div class='table-container'> " + \
        surgical_check_df.style.hide().set_table_styles(
            surgicalStyles).to_html() + "</div>\n"
else:
    pContent += "<div class='table-container'> " + \
        surgical_check_df.to_html(index=False) + "</div>\n"

pContent += "<!-- wp:heading -->\n<h2 class='wp-block-heading'>在院患者手术安排</h2>\n<!-- /wp:heading -->\n"

pContent += "<div class='table-container'> " + \
    inpatient_check_df.to_html(index=False) + "</div>\n"

pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>NEXT患者 {
    nextFromDay_str}_{nextToDay_str}</h2>\n<!-- /wp:heading -->\n"

pContent += "<div class='table-container'> " + \
    surgical_arrange_df.to_html(index=False) + "</div>\n"


# %%

# 筛选出rj_df里 Isroom为“日间“的列
rj_df = surgical_check_df[surgical_check_df['Isroom'] == '日间'].copy()

# rj_df 删除mrn列与pList的mrn相同的行
rj_df = rj_df[~rj_df['mrn'].isin(pList['mrn'])]

# 如果rj_df不为空
if not rj_df.empty:
    # 新建 pBrief 列，格式为 PatientName+mrn+Diagnose
    rj_df.loc[:, 'pBrief'] = rj_df['PatientName'].str.cat(
        rj_df[['mrn', 'Diagnose']].astype(str), sep='+')

    pContent += "<!-- wp:heading {'level':1} -->\n<h1 class='wp-block-heading'>日间手术</h1>\n<!-- /wp:heading -->\n"

    for index, row in rj_df.iterrows():

        pContent += f"<!-- wp:heading -->\n<h2 class='wp-block-heading'>{
            row['pBrief']}</h2>\n<!-- /wp:heading -->\n"

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
    'title': f"患者病情简报 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    'status': 'publish',
    'content': pContent
}
response = requests.post(url, headers=header, json=post, verify=False)
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
